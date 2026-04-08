import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import readline from "node:readline";

import type {
  ActionCatalog,
  AssistantClientEvent,
  AssistantServerEvent,
  ExpertsStatus,
  HealthResponse,
  MemoryNodeSummary,
  QueryRequest,
} from "./types.js";

type RuntimeDaemonCommand = "query" | "health" | "recall" | "experts" | "actions" | "assistant";

type RuntimeDaemonMessage = {
  id: string;
  event: "response" | "token" | "done" | "error" | "assistant";
  payload?: unknown;
  content?: string;
};

export interface RuntimeDaemonTarget {
  host: string;
  port: number;
}

export const DEFAULT_RUNTIME_DAEMON_HOST = "127.0.0.1";
export const DEFAULT_RUNTIME_DAEMON_PORT = 55881;

export function loadRuntimeDaemonTarget(projectRoot: string): RuntimeDaemonTarget | null {
  const statePath = path.join(projectRoot, "tmp", "runtime-daemon", "state.json");
  if (!fs.existsSync(statePath)) {
    return null;
  }
  try {
    const raw = JSON.parse(fs.readFileSync(statePath, "utf8")) as {
      host?: unknown;
      port?: unknown;
    };
    const host = typeof raw.host === "string" && raw.host.trim() ? raw.host.trim() : DEFAULT_RUNTIME_DAEMON_HOST;
    const parsedPort = Number.parseInt(String(raw.port ?? DEFAULT_RUNTIME_DAEMON_PORT), 10);
    return {
      host,
      port: Number.isFinite(parsedPort) ? parsedPort : DEFAULT_RUNTIME_DAEMON_PORT,
    };
  } catch {
    return null;
  }
}

export function resolveRuntimeDaemonTarget(
  projectRoot: string,
  env: NodeJS.ProcessEnv = process.env,
): RuntimeDaemonTarget {
  const stateTarget = loadRuntimeDaemonTarget(projectRoot);
  const host = env.RUNTIME_DAEMON_HOST?.trim() || stateTarget?.host || DEFAULT_RUNTIME_DAEMON_HOST;
  const parsedPort = Number.parseInt(
    env.RUNTIME_DAEMON_PORT?.trim() || String(stateTarget?.port ?? DEFAULT_RUNTIME_DAEMON_PORT),
    10,
  );
  return {
    host,
    port: Number.isFinite(parsedPort) ? parsedPort : DEFAULT_RUNTIME_DAEMON_PORT,
  };
}

async function connectToRuntimeDaemon(target: RuntimeDaemonTarget): Promise<net.Socket> {
  return await new Promise<net.Socket>((resolve, reject) => {
    const socket = net.createConnection(target.port, target.host);
    const onError = (error: Error) => {
      socket.destroy();
      reject(error);
    };
    socket.once("error", onError);
    socket.once("connect", () => {
      socket.off("error", onError);
      resolve(socket);
    });
  });
}

function parseRuntimeDaemonMessage(line: string, requestId: string): RuntimeDaemonMessage | null {
  const message = JSON.parse(line) as RuntimeDaemonMessage;
  return message.id === requestId ? message : null;
}

export class RuntimeDaemonGateway {
  private readonly target: RuntimeDaemonTarget;
  private nextRequestId = 0;

  constructor(target: RuntimeDaemonTarget) {
    this.target = target;
  }

  describeTarget(): string {
    return `${this.target.host}:${this.target.port}`;
  }

  async *query(request: QueryRequest): AsyncIterable<string> {
    const requestId = this.buildRequestId();
    const socket = await connectToRuntimeDaemon(this.target);
    const lineReader = readline.createInterface({ input: socket, crlfDelay: Infinity });
    socket.write(`${JSON.stringify({ id: requestId, command: "query", payload: request })}\n`, "utf8");

    try {
      for await (const line of lineReader) {
        const message = parseRuntimeDaemonMessage(line, requestId);
        if (message === null) {
          continue;
        }
        if (message.event === "token") {
          yield message.content ?? "";
          continue;
        }
        if (message.event === "done") {
          return;
        }
        if (message.event === "error") {
          throw new Error(message.content ?? "Runtime daemon query failed");
        }
      }
      throw new Error(`Runtime daemon closed the query stream unexpectedly (${this.describeTarget()})`);
    } finally {
      lineReader.close();
      socket.end();
      socket.destroy();
    }
  }

  async *assistant(request: AssistantClientEvent): AsyncIterable<AssistantServerEvent> {
    const requestId = this.buildRequestId();
    const socket = await connectToRuntimeDaemon(this.target);
    const lineReader = readline.createInterface({ input: socket, crlfDelay: Infinity });
    socket.write(`${JSON.stringify({ id: requestId, command: "assistant", payload: request })}\n`, "utf8");

    try {
      for await (const line of lineReader) {
        const message = parseRuntimeDaemonMessage(line, requestId);
        if (message === null) {
          continue;
        }
        if (message.event === "assistant") {
          yield message.payload as AssistantServerEvent;
          continue;
        }
        if (message.event === "done") {
          return;
        }
        if (message.event === "error") {
          throw new Error(message.content ?? "Runtime daemon assistant stream failed");
        }
      }
      throw new Error(`Runtime daemon closed the assistant stream unexpectedly (${this.describeTarget()})`);
    } finally {
      lineReader.close();
      socket.end();
      socket.destroy();
    }
  }

  async health(): Promise<HealthResponse> {
    return await this.sendUnaryRequest<HealthResponse>("health", {});
  }

  async recall(query: string): Promise<MemoryNodeSummary[]> {
    return await this.sendUnaryRequest<MemoryNodeSummary[]>("recall", { query, limit: 5 });
  }

  async experts(): Promise<ExpertsStatus> {
    return await this.sendUnaryRequest<ExpertsStatus>("experts", {});
  }

  async actions(): Promise<ActionCatalog> {
    return await this.sendUnaryRequest<ActionCatalog>("actions", {});
  }

  async close(): Promise<void> {
    return;
  }

  private async sendUnaryRequest<T>(command: Exclude<RuntimeDaemonCommand, "query" | "assistant">, payload: object): Promise<T> {
    const requestId = this.buildRequestId();
    const socket = await connectToRuntimeDaemon(this.target);
    const lineReader = readline.createInterface({ input: socket, crlfDelay: Infinity });
    socket.write(`${JSON.stringify({ id: requestId, command, payload })}\n`, "utf8");

    try {
      for await (const line of lineReader) {
        const message = parseRuntimeDaemonMessage(line, requestId);
        if (message === null) {
          continue;
        }
        if (message.event === "response") {
          return message.payload as T;
        }
        if (message.event === "error") {
          throw new Error(message.content ?? `Runtime daemon ${command} request failed`);
        }
      }
      throw new Error(`Runtime daemon closed the ${command} request unexpectedly (${this.describeTarget()})`);
    } finally {
      lineReader.close();
      socket.end();
      socket.destroy();
    }
  }

  private buildRequestId(): string {
    this.nextRequestId += 1;
    return `node-runtime-${this.nextRequestId}`;
  }
}
