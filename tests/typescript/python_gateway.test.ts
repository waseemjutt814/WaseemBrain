import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { PythonCoordinatorGateway } from "../../interface/src/python_gateway.js";
import { createServer } from "../../interface/src/server.js";

test("python gateway serves live coordinator-backed routes", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "waseem-brain-gateway-"));
  const gateway = new PythonCoordinatorGateway({
    pythonExecutable: process.env.PYTHON_EXECUTABLE,
    bridgePath: path.resolve(process.cwd(), "scripts", "coordinator_bridge.py"),
    env: {
      ...process.env,
      EXPERT_DIR: path.resolve(process.cwd(), "experts", "base"),
      CHROMA_DIR: path.join(tempRoot, "data", "chroma"),
      SQLITE_DIR: path.join(tempRoot, "data", "sqlite"),
      EMBEDDING_BACKEND: "hash",
      MEMORY_VECTOR_BACKEND: "hnsw",
      EMOTION_TEXT_BACKEND: "heuristic",
      INTERNET_ENABLED: "false",
    },
  });
  const app = createServer(gateway);

  try {
    const initialHealth = await app.inject({ method: "GET", url: "/health" });
    assert.equal(initialHealth.statusCode, 200);
    const initialHealthPayload = JSON.parse(initialHealth.body);
    assert.ok(initialHealthPayload.knowledge.cards >= 21);
    assert.equal(initialHealthPayload.memory_node_count, initialHealthPayload.knowledge.cards);

    const query = await app.inject({
      method: "POST",
      url: "/query",
      payload: { input: "what is the capital of France", modality: "text", session_id: "ts-1" },
    });
    assert.equal(query.statusCode, 200);
    assert.match(query.body.toLowerCase(), /france/);

    const experts = await app.inject({ method: "GET", url: "/experts" });
    assert.equal(experts.statusCode, 200);
    assert.deepEqual(JSON.parse(experts.body), {
      loaded: ["geography"],
      count: 1,
    });

    const recall = await app.inject({ method: "GET", url: "/memory/recall?q=france" });
    assert.equal(recall.statusCode, 200);
    const recallPayload = JSON.parse(recall.body);
    assert.ok(recallPayload.length >= 1);
    assert.ok(
      recallPayload.some((item: { content: string }) => item.content.toLowerCase().includes("france")),
    );

    const health = await app.inject({ method: "GET", url: "/health" });
    assert.equal(health.statusCode, 200);
    const finalHealthPayload = JSON.parse(health.body);
    assert.ok(finalHealthPayload.memory_node_count >= initialHealthPayload.memory_node_count + 1);
  } finally {
    await app.close();
    await fs.rm(tempRoot, { recursive: true, force: true });
  }
});
