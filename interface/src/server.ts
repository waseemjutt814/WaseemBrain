import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import multipart from "@fastify/multipart";
import staticPlugin from "@fastify/static";
import websocket from "@fastify/websocket";
import Fastify, { type FastifyInstance } from "fastify";

import { PythonCoordinatorGateway } from "./python_gateway.js";
import { registerActionsRoute } from "./routes/actions.js";
import { registerCatalogRoute } from "./routes/catalog.js";
import { registerExpertsRoute } from "./routes/experts.js";
import { registerHealthRoute } from "./routes/health.js";
import { registerMemoryRoute } from "./routes/memory.js";
import { registerQueryRoute } from "./routes/query.js";
import {
  RuntimeDaemonGateway,
  loadRuntimeDaemonTarget,
  resolveRuntimeDaemonTarget,
} from "./runtime_daemon_gateway.js";
import type {
  ActionCatalog,
  AssistantClientEvent,
  AssistantServerEvent,
  ExpertsStatus,
  MemoryNodeSummary,
  QueryRequest,
} from "./types.js";
import { registerAssistantWebsocketRoute } from "./ws/assistant.js";
import { registerWebsocketRoute } from "./ws/handler.js";

const currentModulePath = fileURLToPath(import.meta.url);

function resolveExistingPath(...candidates: string[]): string {
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return candidates[0] ?? process.cwd();
}

export type GatewayMode = "auto" | "bridge" | "daemon";

export interface RuntimePaths {
  projectRoot: string;
  publicDir: string;
  generatedDir: string | null;
  assetsDir?: string | null;
  bridgePath: string;
  pythonRunnerPath?: string;
  manageRuntimeDaemonPath?: string;
}

export function resolveRuntimePaths(
  modulePath: string = currentModulePath,
  cwd: string = process.cwd(),
): RuntimePaths {
  const moduleDir = path.dirname(modulePath);
  const projectRoot = resolveExistingPath(path.resolve(moduleDir, "..", ".."), cwd);
  const publicDir = resolveExistingPath(
    path.resolve(projectRoot, "interface", "public"),
    path.resolve(moduleDir, "..", "public"),
  );
  const generatedCandidate = path.resolve(projectRoot, "interface", "generated");
  const generatedDir = fs.existsSync(generatedCandidate) ? generatedCandidate : null;
  const assetsCandidate = path.resolve(projectRoot, "assets");
  const assetsDir = fs.existsSync(assetsCandidate) ? assetsCandidate : null;
  const bridgePath = resolveExistingPath(
    path.resolve(projectRoot, "scripts", "coordinator_bridge.py"),
    path.resolve(moduleDir, "..", "..", "scripts", "coordinator_bridge.py"),
    path.resolve(cwd, "scripts", "coordinator_bridge.py"),
  );
  const pythonRunnerPath = resolveExistingPath(
    path.resolve(projectRoot, "scripts", "run_python.mjs"),
    path.resolve(moduleDir, "..", "..", "scripts", "run_python.mjs"),
    path.resolve(cwd, "scripts", "run_python.mjs"),
  );
  const manageRuntimeDaemonPath = resolveExistingPath(
    path.resolve(projectRoot, "scripts", "manage_runtime_daemon.py"),
    path.resolve(moduleDir, "..", "..", "scripts", "manage_runtime_daemon.py"),
    path.resolve(cwd, "scripts", "manage_runtime_daemon.py"),
  );
  return {
    projectRoot,
    publicDir,
    generatedDir,
    assetsDir,
    bridgePath,
    pythonRunnerPath,
    manageRuntimeDaemonPath,
  };
}

export function resolveGatewayMode(env: NodeJS.ProcessEnv = process.env): GatewayMode {
  const raw = env.WB_GATEWAY_MODE?.trim().toLowerCase();
  if (raw === "bridge" || raw === "daemon") {
    return raw;
  }
  return "auto";
}

export interface CoordinatorGateway {
  query(request: QueryRequest): AsyncIterable<string>;
  health(): Promise<Record<string, unknown>>;
  recall(query: string): Promise<MemoryNodeSummary[]>;
  experts(): Promise<ExpertsStatus>;
  actions?(): Promise<ActionCatalog>;
  assistant?(request: AssistantClientEvent): AsyncIterable<AssistantServerEvent>;
  close?(): Promise<void>;
}

export function shouldUseRuntimeDaemon(
  runtimePaths: RuntimePaths = resolveRuntimePaths(),
  env: NodeJS.ProcessEnv = process.env,
): boolean {
  const gatewayMode = resolveGatewayMode(env);
  if (gatewayMode === "daemon") {
    return true;
  }
  if (gatewayMode === "bridge") {
    return false;
  }
  return (
    loadRuntimeDaemonTarget(runtimePaths.projectRoot) !== null ||
    Boolean(env.RUNTIME_DAEMON_HOST?.trim()) ||
    Boolean(env.RUNTIME_DAEMON_PORT?.trim())
  );
}

function createPythonBridgeGateway(
  runtimePaths: RuntimePaths,
  env: NodeJS.ProcessEnv = process.env,
): CoordinatorGateway {
  return new PythonCoordinatorGateway({
    pythonExecutable: env.PYTHON_EXECUTABLE,
    bridgePath: env.COORDINATOR_BRIDGE_PATH ?? runtimePaths.bridgePath,
    cwd: runtimePaths.projectRoot,
    env: { ...env, REPO_ROOT: env.REPO_ROOT ?? runtimePaths.projectRoot },
  });
}

export function createBootstrapGateway(
  runtimePaths: RuntimePaths = resolveRuntimePaths(),
  env: NodeJS.ProcessEnv = process.env,
): CoordinatorGateway {
  if (shouldUseRuntimeDaemon(runtimePaths, env)) {
    return new RuntimeDaemonGateway(resolveRuntimeDaemonTarget(runtimePaths.projectRoot, env));
  }
  return createPythonBridgeGateway(runtimePaths, env);
}

function isLocalRuntimeTarget(env: NodeJS.ProcessEnv = process.env): boolean {
  const host = env.RUNTIME_DAEMON_HOST?.trim().toLowerCase();
  if (!host) {
    return true;
  }
  return ["127.0.0.1", "localhost", "0.0.0.0"].includes(host);
}

function maybeAutostartRuntimeDaemon(
  runtimePaths: RuntimePaths,
  env: NodeJS.ProcessEnv = process.env,
): void {
  const gatewayMode = resolveGatewayMode(env);
  if (gatewayMode === "bridge" || !isLocalRuntimeTarget(env)) {
    return;
  }
  if (!runtimePaths.pythonRunnerPath || !runtimePaths.manageRuntimeDaemonPath) {
    return;
  }
  if (!fs.existsSync(runtimePaths.pythonRunnerPath) || !fs.existsSync(runtimePaths.manageRuntimeDaemonPath)) {
    return;
  }

  const result = spawnSync(
    process.execPath,
    [runtimePaths.pythonRunnerPath, runtimePaths.manageRuntimeDaemonPath, "start"],
    {
      cwd: runtimePaths.projectRoot,
      env: { ...env, REPO_ROOT: env.REPO_ROOT ?? runtimePaths.projectRoot },
      encoding: "utf8",
    },
  );
  const output = `${result.stdout ?? ""}${result.stderr ?? ""}`.trim();
  if (result.status === 0) {
    if (output) {
      console.log(`[INFO] ${output}`);
    }
    return;
  }
  if (gatewayMode === "daemon") {
    throw new Error(`Runtime daemon auto-start failed.\n${output}`.trim());
  }
  if (output) {
    console.warn(`[WARN] Runtime daemon auto-start failed. Falling back to the Python bridge.\n${output}`);
  }
}

export function createServer(
  gateway: CoordinatorGateway,
  runtimePaths: RuntimePaths = resolveRuntimePaths(),
): FastifyInstance {
  const app = Fastify({ logger: false });

  void app.register(multipart);
  void app.register(websocket);
  void registerHealthRoute(app, gateway);
  void registerMemoryRoute(app, gateway);
  void registerExpertsRoute(app, gateway);
  void registerCatalogRoute(app, gateway);
  void registerActionsRoute(app, gateway);

  if (runtimePaths.generatedDir) {
    void app.register(staticPlugin, {
      root: runtimePaths.generatedDir,
      prefix: "/generated/",
      decorateReply: false,
    });
  }

  if (runtimePaths.assetsDir) {
    void app.register(staticPlugin, {
      root: runtimePaths.assetsDir,
      prefix: "/assets/",
      decorateReply: false,
    });
  }

  void app.register(staticPlugin, {
    root: runtimePaths.publicDir,
    prefix: "/",
    decorateReply: false,
  });

  void app.after(() => {
    registerQueryRoute(app, gateway);
    registerWebsocketRoute(app, gateway);
    registerAssistantWebsocketRoute(app, gateway);
    app.get("/", async (_request, reply) => reply.redirect("/chat.html"));
  });

  void app.addHook("onClose", async () => {
    if (typeof gateway.close === "function") {
      await gateway.close();
    }
  });

  return app;
}

function describeGateway(gateway: CoordinatorGateway, runtimePaths: RuntimePaths): string {
  if (gateway instanceof RuntimeDaemonGateway) {
    return `runtime daemon at ${gateway.describeTarget()}`;
  }
  if (gateway instanceof PythonCoordinatorGateway) {
    return `python bridge at ${path.relative(runtimePaths.projectRoot, runtimePaths.bridgePath)}`;
  }
  return "custom coordinator gateway";
}

function shouldAutoOpenBrowser(env: NodeJS.ProcessEnv = process.env): boolean {
  const raw = env.WB_AUTO_OPEN_BROWSER?.trim().toLowerCase();
  if (!raw) {
    return true;
  }
  return !["0", "false", "no", "off"].includes(raw);
}

async function bootstrap(): Promise<void> {
  const runtimePaths = resolveRuntimePaths();
  const gatewayMode = resolveGatewayMode();
  maybeAutostartRuntimeDaemon(runtimePaths);
  let gateway = createBootstrapGateway(runtimePaths);

  try {
    await gateway.health();
  } catch (error) {
    if (gatewayMode === "auto" && gateway instanceof RuntimeDaemonGateway) {
      console.warn("[WARN] Runtime daemon was discovered but not reachable. Falling back to the Python bridge.");
      await gateway.close?.();
      gateway = createPythonBridgeGateway(runtimePaths);
      await gateway.health();
    } else {
      throw error;
    }
  }

  const app = createServer(gateway, runtimePaths);
  const port = Number.parseInt(process.env.API_PORT ?? "8080", 10);
  const host = process.env.API_HOST?.trim() || "127.0.0.1";
  await app.listen({ port, host });

  const url = `http://${host}:${port}`;
  console.log(`\n[INFO] Waseem Brain Interface is live at: ${url}`);
  console.log(`[INFO] Backend gateway: ${describeGateway(gateway, runtimePaths)}`);
  console.log("[INFO] Press Ctrl+C to stop the server.\n");

  if (process.platform === "win32" && shouldAutoOpenBrowser()) {
    const { exec } = await import("node:child_process");
    exec(`start ${url}`);
  }
}

const executedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (executedPath === currentModulePath) {
  void bootstrap();
}
