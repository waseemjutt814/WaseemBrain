import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  createBootstrapGateway,
  createServer,
  resolveGatewayMode,
  resolveRuntimePaths,
  shouldUseRuntimeDaemon,
} from "../../interface/src/server.js";
import { RuntimeDaemonGateway } from "../../interface/src/runtime_daemon_gateway.js";

const healthPayload = {
  status: "ok" as const,
  project_name: "Waseem Brain",
  condition: "ready" as const,
  condition_summary: "runtime healthy",
  ready: true,
  experts_loaded: 1,
  experts_available: 3,
  expert_ids: ["language-en"],
  memory_node_count: 2,
  uptime_sec: 1,
  router_backend: "local",
  vector_backend: "hnsw",
  capabilities: {
    model_free_core: true,
    api_key_required: false,
    self_improvement_scope: "knowledge-only",
    router_acceleration_optional: true,
    default_router_backend: "local",
  },
  components: {
    router_artifact: "ready",
    expert_registry: "ready",
    response_policy: "ready",
    router_daemon: "not-needed",
    internet: "enabled",
  },
  learning: {
    enabled: true,
    backend: "offline",
    response_policy: "ready",
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
    version: "general-knowledge@2026.03",
    dataset_ids: ["general-knowledge"],
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

test("resolveRuntimePaths prefers dist-local assets and bridge scripts", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "waseem-brain-paths-"));
  const distRoot = path.join(tempRoot, "dist");
  const modulePath = path.join(distRoot, "interface", "src", "server.js");
  const publicDir = path.join(distRoot, "interface", "public");
  const generatedDir = path.join(distRoot, "interface", "generated");
  const scriptsDir = path.join(distRoot, "scripts");
  const assetsDir = path.join(distRoot, "assets");

  await fs.mkdir(publicDir, { recursive: true });
  await fs.mkdir(generatedDir, { recursive: true });
  await fs.mkdir(scriptsDir, { recursive: true });
  await fs.mkdir(assetsDir, { recursive: true });
  await fs.writeFile(path.join(publicDir, "chat.html"), "chat", "utf8");
  await fs.writeFile(path.join(generatedDir, "app.js"), "console.log('app');", "utf8");
  await fs.writeFile(path.join(scriptsDir, "coordinator_bridge.py"), "print('bridge')", "utf8");
  await fs.writeFile(path.join(assetsDir, "waseembrain-emoji.svg"), "<svg></svg>", "utf8");

  const resolved = resolveRuntimePaths(modulePath, path.join(tempRoot, "repo-root"));
  assert.equal(resolved.projectRoot, distRoot);
  assert.equal(resolved.publicDir, publicDir);
  assert.equal(resolved.generatedDir, generatedDir);
  assert.equal(resolved.assetsDir, assetsDir);
  assert.equal(resolved.bridgePath, path.join(scriptsDir, "coordinator_bridge.py"));

  await fs.rm(tempRoot, { recursive: true, force: true });
});

test("bootstrap gateway respects explicit bridge and daemon preferences", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "waseem-brain-gateway-"));
  const publicDir = path.join(tempRoot, "interface", "public");
  const scriptsDir = path.join(tempRoot, "scripts");
  const daemonStateDir = path.join(tempRoot, "tmp", "runtime-daemon");
  await fs.mkdir(publicDir, { recursive: true });
  await fs.mkdir(scriptsDir, { recursive: true });
  await fs.mkdir(daemonStateDir, { recursive: true });
  await fs.writeFile(path.join(publicDir, "chat.html"), "chat", "utf8");
  await fs.writeFile(path.join(scriptsDir, "coordinator_bridge.py"), "print('bridge')", "utf8");
  await fs.writeFile(
    path.join(daemonStateDir, "state.json"),
    JSON.stringify({ host: "127.0.0.1", port: 55881 }),
    "utf8",
  );

  const runtimePaths = {
    projectRoot: tempRoot,
    publicDir,
    generatedDir: null,
    assetsDir: null,
    bridgePath: path.join(scriptsDir, "coordinator_bridge.py"),
  };

  assert.equal(resolveGatewayMode({ WB_GATEWAY_MODE: "daemon" } as NodeJS.ProcessEnv), "daemon");
  assert.equal(resolveGatewayMode({ WB_GATEWAY_MODE: "bridge" } as NodeJS.ProcessEnv), "bridge");
  assert.equal(resolveGatewayMode({} as NodeJS.ProcessEnv), "auto");
  assert.equal(shouldUseRuntimeDaemon(runtimePaths, {} as NodeJS.ProcessEnv), true);
  assert.equal(
    shouldUseRuntimeDaemon(runtimePaths, { WB_GATEWAY_MODE: "bridge" } as NodeJS.ProcessEnv),
    false,
  );

  const daemonGateway = createBootstrapGateway(
    runtimePaths,
    {
      WB_GATEWAY_MODE: "daemon",
      RUNTIME_DAEMON_HOST: "127.0.0.1",
      RUNTIME_DAEMON_PORT: "55881",
    } as NodeJS.ProcessEnv,
  );
  assert.ok(daemonGateway instanceof RuntimeDaemonGateway);
  await daemonGateway.close?.();

  const bridgeGateway = createBootstrapGateway(
    runtimePaths,
    { WB_GATEWAY_MODE: "bridge" } as NodeJS.ProcessEnv,
  );
  assert.equal(bridgeGateway instanceof RuntimeDaemonGateway, false);
  await bridgeGateway.close?.();

  await fs.rm(tempRoot, { recursive: true, force: true });
});

test("server serves generated browser assets from the runtime path set", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "waseem-brain-generated-"));
  const publicDir = path.join(tempRoot, "interface", "public");
  const generatedDir = path.join(tempRoot, "interface", "generated");
  const scriptsDir = path.join(tempRoot, "scripts");
  const assetsDir = path.join(tempRoot, "assets");
  await fs.mkdir(publicDir, { recursive: true });
  await fs.mkdir(generatedDir, { recursive: true });
  await fs.mkdir(scriptsDir, { recursive: true });
  await fs.mkdir(assetsDir, { recursive: true });
  await fs.writeFile(path.join(publicDir, "chat.html"), "<html>chat</html>", "utf8");
  await fs.writeFile(path.join(generatedDir, "app.js"), "console.log('generated');", "utf8");
  await fs.writeFile(path.join(scriptsDir, "coordinator_bridge.py"), "print('bridge')", "utf8");
  await fs.writeFile(path.join(assetsDir, "waseembrain-emoji.svg"), "<svg>emoji</svg>", "utf8");

  const app = createServer(
    {
      async *query(): AsyncIterable<string> {
        yield "ok";
      },
      async health() {
        return healthPayload;
      },
      async recall() {
        return [];
      },
      async experts() {
        return { loaded: ["language-en"], count: 1 };
      },
    },
    {
      projectRoot: tempRoot,
      publicDir,
      generatedDir,
      assetsDir,
      bridgePath: path.join(scriptsDir, "coordinator_bridge.py"),
    },
  );

  try {
    const generatedResponse = await app.inject({ method: "GET", url: "/generated/app.js" });
    assert.equal(generatedResponse.statusCode, 200);
    assert.match(generatedResponse.body, /generated/);

    const assetResponse = await app.inject({ method: "GET", url: "/assets/waseembrain-emoji.svg" });
    assert.equal(assetResponse.statusCode, 200);
    assert.match(assetResponse.body, /emoji/);
  } finally {
    await app.close();
    await fs.rm(tempRoot, { recursive: true, force: true });
  }
});