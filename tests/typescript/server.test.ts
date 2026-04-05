import test from "node:test";
import assert from "node:assert/strict";

import { createServer } from "../../interface/src/server.js";
import type { QueryRequest } from "../../interface/src/types.js";

const healthPayload = {
  status: "ok" as const,
  project_name: "Waseem Brain",
  condition: "ready" as const,
  condition_summary: "response policy still in rule-default mode",
  ready: true,
  experts_loaded: 1,
  experts_available: 3,
  expert_ids: ["language-en", "code-general", "geography"],
  memory_node_count: 2,
  uptime_sec: 3,
  router_backend: "local",
  vector_backend: "hnsw",
  components: {
    router_artifact: "ready",
    expert_registry: "ready",
    response_policy: "rule-default",
    router_daemon: "not-needed",
    internet: "enabled",
  },
  learning: {
    enabled: true,
    backend: "offline",
    response_policy: "rule-default",
    trace_files: 0,
    trace_turns: 0,
    expert_trace_files: 0,
    expert_trace_turns: 0,
    training_jobs: 0,
    datasets: 0,
    trained_trace_count: 0,
    last_event: "runtime initialized",
    phase: "collecting-real-traces",
  },
  knowledge: {
    status: "ready",
    datasets: 2,
    cards: 21,
    seeded_cards: 21,
    seeded_this_run: 0,
    source_dir: "experts/bootstrap",
    version: "general-knowledge@2026.03|coding-handbook@2026.03",
    dataset_ids: ["general-knowledge", "coding-handbook"],
    last_seeded_at: 1,
    note: "built-in knowledge is available",
  },
  router: {
    mode: "local",
    artifact: "ready",
    target: "127.0.0.1:50051",
    daemon_state: "not-needed",
  },
  storage: {
    sqlite_path: "data/sqlite/metadata.db",
    vector_index_path: "data/chroma/memory.index",
    router_artifact_path: "experts/router.json",
    response_policy_path: "experts/response-policy.json",
    trace_dir: "experts/lora/traces",
  },
};

function buildMultipartBody(
  filename: string,
  mimeType: string,
  content: string,
): { body: string; contentType: string } {
  const boundary = "----waseem-brain-boundary";
  const body =
    `--${boundary}\r\n` +
    `Content-Disposition: form-data; name="file"; filename="${filename}"\r\n` +
    `Content-Type: ${mimeType}\r\n\r\n` +
    `${content}\r\n` +
    `--${boundary}--\r\n`;
  return {
    body,
    contentType: `multipart/form-data; boundary=${boundary}`,
  };
}

type BinaryCapturedRequest = {
  modality: "file" | "voice";
  filename: string;
  mime_type: string;
  session_id: string;
  input_base64: string;
};

test("health and memory routes respond", async () => {
  const app = createServer({
    async *query(): AsyncIterable<string> {
      yield "hello";
    },
    async health() {
      return healthPayload;
    },
    async recall() {
      return [{ id: "mem-1", content: "hello", confidence: 0.9, source: "test" }];
    },
    async experts() {
      return { loaded: ["language-en"], count: 1 };
    },
  });

  const health = await app.inject({ method: "GET", url: "/health" });
  assert.equal(health.statusCode, 200);

  const memory = await app.inject({ method: "GET", url: "/memory/recall?q=hello" });
  assert.equal(memory.statusCode, 200);

  const query = await app.inject({ method: "POST", url: "/query", payload: { input: "hello", modality: "text", session_id: "s-1" } });
  assert.equal(query.statusCode, 200);
  await app.close();
});

test("query route returns 500 when stream fails before first token", async () => {
  const app = createServer({
    async *query(): AsyncIterable<string> {
      throw new Error("broken gateway");
    },
    async health() {
      return { ...healthPayload, experts_loaded: 0, memory_node_count: 0, uptime_sec: 0 };
    },
    async recall() {
      return [];
    },
    async experts() {
      return { loaded: [], count: 0 };
    },
  });

  const query = await app.inject({
    method: "POST",
    url: "/query",
    payload: { input: "hello", modality: "text", session_id: "s-1" },
  });
  assert.equal(query.statusCode, 500);
  assert.match(query.body, /broken gateway/);
  await app.close();
});

test("query route appends stream error after partial output", async () => {
  const app = createServer({
    async *query(): AsyncIterable<string> {
      yield "hello ";
      throw new Error("late failure");
    },
    async health() {
      return { ...healthPayload, experts_loaded: 0, memory_node_count: 0, uptime_sec: 0 };
    },
    async recall() {
      return [];
    },
    async experts() {
      return { loaded: [], count: 0 };
    },
  });

  const query = await app.inject({
    method: "POST",
    url: "/query",
    payload: { input: "hello", modality: "text", session_id: "s-1" },
  });
  assert.equal(query.statusCode, 200);
  assert.match(query.body, /hello/);
  assert.match(query.body, /\[stream-error\] late failure/);
  await app.close();
});

test("file and voice routes accept multipart uploads on the root app", async () => {
  const captured: QueryRequest[] = [];
  const app = createServer({
    async *query(request: QueryRequest): AsyncIterable<string> {
      captured.push(request);
      yield "ok";
    },
    async health() {
      return healthPayload;
    },
    async recall() {
      return [];
    },
    async experts() {
      return { loaded: [], count: 0 };
    },
  });

  const filePayload = buildMultipartBody("notes.txt", "text/plain", "hello from file");
  const fileResponse = await app.inject({
    method: "POST",
    url: "/query/file?session_id=file-session",
    headers: { "content-type": filePayload.contentType },
    payload: filePayload.body,
  });
  assert.equal(fileResponse.statusCode, 200);
  assert.match(fileResponse.body, /ok/);

  const voicePayload = buildMultipartBody("voice.wav", "audio/wav", "voice-bytes");
  const voiceResponse = await app.inject({
    method: "POST",
    url: "/query/voice?session_id=voice-session",
    headers: { "content-type": voicePayload.contentType },
    payload: voicePayload.body,
  });
  assert.equal(voiceResponse.statusCode, 200);
  assert.match(voiceResponse.body, /ok/);

  assert.equal(captured.length, 2);
  const fileRequest = captured[0] as BinaryCapturedRequest;
  const voiceRequest = captured[1] as BinaryCapturedRequest;
  assert.deepEqual(
    [
      {
        modality: fileRequest.modality,
        filename: fileRequest.filename,
        mime_type: fileRequest.mime_type,
        session_id: fileRequest.session_id,
      },
      {
        modality: voiceRequest.modality,
        filename: voiceRequest.filename,
        mime_type: voiceRequest.mime_type,
        session_id: voiceRequest.session_id,
      },
    ],
    [
      {
        modality: "file",
        filename: "notes.txt",
        mime_type: "text/plain",
        session_id: "file-session",
      },
      {
        modality: "voice",
        filename: "voice.wav",
        mime_type: "audio/wav",
        session_id: "voice-session",
      },
    ],
  );
  assert.equal(Buffer.from(fileRequest.input_base64, "base64").toString("utf-8"), "hello from file");
  assert.equal(Buffer.from(voiceRequest.input_base64, "base64").toString("utf-8"), "voice-bytes");
  await app.close();
});
