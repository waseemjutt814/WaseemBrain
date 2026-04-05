import path from "node:path";
import { fileURLToPath } from "node:url";

import multipart from "@fastify/multipart";
import staticPlugin from "@fastify/static";
import websocket from "@fastify/websocket";
import Fastify, { type FastifyInstance } from "fastify";

import { PythonCoordinatorGateway } from "./python_gateway.js";
import { registerExpertsRoute } from "./routes/experts.js";
import { registerHealthRoute } from "./routes/health.js";
import { registerMemoryRoute } from "./routes/memory.js";
import { registerQueryRoute } from "./routes/query.js";
import { registerWebsocketRoute } from "./ws/handler.js";
import type { ExpertsStatus, HealthResponse, MemoryNodeSummary, QueryRequest } from "./types.js";

export interface CoordinatorGateway {
  query(request: QueryRequest): AsyncIterable<string>;
  health(): Promise<HealthResponse>;
  recall(query: string): Promise<MemoryNodeSummary[]>;
  experts(): Promise<ExpertsStatus>;
  close?(): Promise<void>;
}

export function createServer(gateway: CoordinatorGateway): FastifyInstance {
  const app = Fastify({ logger: false });

  void app.register(multipart);
  void app.register(websocket);
  void registerHealthRoute(app, gateway);
  void registerMemoryRoute(app, gateway);
  void registerExpertsRoute(app, gateway);
  const publicDir = path.resolve(process.cwd(), "interface", "public");
  void app.register(staticPlugin, { root: publicDir, prefix: "/" });
  void app.after(() => {
    registerQueryRoute(app, gateway);
    registerWebsocketRoute(app, gateway);
    app.get("/", async (request, reply) => {
      return reply.redirect("/chat.html");
    });
  });
  void app.addHook("onClose", async () => {
    if (typeof gateway.close === "function") {
      await gateway.close();
    }
  });

  return app;
}

export function createBootstrapGateway(): CoordinatorGateway {
  return new PythonCoordinatorGateway({
    pythonExecutable: process.env.PYTHON_EXECUTABLE,
    bridgePath:
      process.env.COORDINATOR_BRIDGE_PATH ??
      path.resolve(process.cwd(), "scripts", "coordinator_bridge.py"),
  });
}

async function bootstrap(): Promise<void> {
  const gateway = createBootstrapGateway();
  await gateway.health();
  const app = createServer(gateway);
  const port = Number.parseInt(process.env.API_PORT ?? "8080", 10);
  const host = "127.0.0.1";
  await app.listen({ port, host });
  
  const url = `http://${host}:${port}`;
  console.log(`\n[INFO] Lattice Brain Interface is live at: ${url}`);
  console.log("[INFO] Press Ctrl+C to stop the server.\n");

  // Auto-open browser on Windows
  if (process.platform === "win32") {
    const { exec } = await import("node:child_process");
    exec(`start ${url}`);
  }
}

const currentModulePath = fileURLToPath(import.meta.url);
const executedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";

if (executedPath === currentModulePath) {
  void bootstrap();
}
