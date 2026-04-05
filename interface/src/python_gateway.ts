import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import path from "node:path";
import readline from "node:readline";

import type {
  ExpertsStatus,
  HealthResponse,
  MemoryNodeSummary,
  QueryRequest,
} from "./types.js";

type BridgeCommand = "query" | "health" | "recall" | "experts" | "shutdown";

type BridgeResponse = {
  id: string;
  event: "response" | "token" | "done" | "error";
  payload?: unknown;
  content?: string;
};

type PendingUnary = {
  resolve(value: unknown): void;
  reject(error: Error): void;
};

type PythonCoordinatorGatewayOptions = {
  pythonExecutable?: string;
  bridgePath?: string;
  cwd?: string;
  env?: NodeJS.ProcessEnv;
};

class AsyncTokenQueue implements AsyncIterable<string>, AsyncIterator<string> {
  private items: string[] = [];
  private waiters: Array<(value: IteratorResult<string>) => void> = [];
  private failure: Error | null = null;
  private finished = false;

  push(value: string): void {
    if (this.finished || this.failure) {
      return;
    }
    const waiter = this.waiters.shift();
    if (waiter) {
      waiter({ value, done: false });
      return;
    }
    this.items.push(value);
  }

  complete(): void {
    if (this.finished || this.failure) {
      return;
    }
    this.finished = true;
    while (this.waiters.length > 0) {
      const waiter = this.waiters.shift();
      waiter?.({ value: undefined, done: true });
    }
  }

  fail(error: Error): void {
    if (this.finished || this.failure) {
      return;
    }
    this.failure = error;
    while (this.waiters.length > 0) {
      const waiter = this.waiters.shift();
      waiter?.(Promise.reject(error) as never);
    }
  }

  async next(): Promise<IteratorResult<string>> {
    if (this.items.length > 0) {
      return { value: this.items.shift()!, done: false };
    }
    if (this.failure) {
      throw this.failure;
    }
    if (this.finished) {
      return { value: undefined, done: true };
    }
    return await new Promise<IteratorResult<string>>((resolve) => {
      this.waiters.push(resolve);
    });
  }

  [Symbol.asyncIterator](): AsyncIterator<string> {
    return this;
  }
}

export class PythonCoordinatorGateway {
  private readonly options: PythonCoordinatorGatewayOptions;
  private process: ChildProcessWithoutNullStreams | null = null;
  private readonly pendingUnary = new Map<string, PendingUnary>();
  private readonly pendingStreams = new Map<string, AsyncTokenQueue>();
  private nextRequestId = 0;
  private recentStderr = "";
  private closing = false;

  constructor(options: PythonCoordinatorGatewayOptions = {}) {
    this.options = options;
  }

  async *query(request: QueryRequest): AsyncIterable<string> {
    const requestId = this.sendStreamingRequest("query", request);
    const queue = this.pendingStreams.get(requestId);
    if (!queue) {
      throw new Error("Bridge stream was not initialized");
    }
    try {
      for await (const token of queue) {
        yield token;
      }
    } finally {
      this.pendingStreams.delete(requestId);
    }
  }

  async health(): Promise<HealthResponse> {
    return this.sendUnaryRequest<HealthResponse>("health", {});
  }

  async recall(query: string): Promise<MemoryNodeSummary[]> {
    return this.sendUnaryRequest<MemoryNodeSummary[]>("recall", { query, limit: 5 });
  }

  async experts(): Promise<ExpertsStatus> {
    return this.sendUnaryRequest<ExpertsStatus>("experts", {});
  }

  async close(): Promise<void> {
    const child = this.process;
    if (!child) {
      return;
    }
    this.closing = true;

    try {
      this.writeMessage({ id: this.buildRequestId(), command: "shutdown", payload: {} });
    } catch {
      child.kill();
      return;
    }

    await new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        child.kill();
        resolve();
      }, 500);
      child.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });
      child.stdin.end();
    });
  }

  private sendStreamingRequest(command: BridgeCommand, payload: object): string {
    this.ensureProcess();
    const requestId = this.buildRequestId();
    this.pendingStreams.set(requestId, new AsyncTokenQueue());
    this.writeMessage({ id: requestId, command, payload });
    return requestId;
  }

  private async sendUnaryRequest<T>(command: BridgeCommand, payload: object): Promise<T> {
    this.ensureProcess();
    const requestId = this.buildRequestId();
    const promise = new Promise<T>((resolve, reject) => {
      this.pendingUnary.set(requestId, {
        resolve(value: unknown) {
          resolve(value as T);
        },
        reject,
      });
    });
    this.writeMessage({ id: requestId, command, payload });
    return promise;
  }

  private ensureProcess(): void {
    if (this.process) {
      return;
    }

    const pythonExecutable =
      this.options.pythonExecutable ??
      process.env.PYTHON_EXECUTABLE ??
      (process.platform === "win32" ? "python" : "python3");
    const bridgePath =
      this.options.bridgePath ??
      path.resolve(this.options.cwd ?? process.cwd(), "scripts", "coordinator_bridge.py");
    const env = {
      ...process.env,
      ...this.options.env,
      PYTHONUNBUFFERED: "1",
    };
    const child = spawn(pythonExecutable, [bridgePath], {
      cwd: this.options.cwd ?? process.cwd(),
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.process = child;

    const stdoutReader = readline.createInterface({ input: child.stdout });
    stdoutReader.on("line", (line) => {
      this.handleBridgeLine(line);
    });

    child.stderr.on("data", (chunk: Buffer | string) => {
      this.recentStderr = `${this.recentStderr}${chunk.toString("utf-8")}`.slice(-4000);
    });

    child.once("error", (error) => {
      this.failAll(error instanceof Error ? error : new Error(String(error)));
    });

    child.once("exit", (code, signal) => {
      if (this.closing) {
        this.process = null;
        this.closing = false;
        return;
      }
      const details = this.recentStderr.trim();
      const suffix = details ? `\n${details}` : "";
      const error = new Error(
        `Python bridge exited unexpectedly (code=${code ?? "null"}, signal=${signal ?? "null"})${suffix}`,
      );
      this.failAll(error);
      this.process = null;
    });
  }

  private handleBridgeLine(line: string): void {
    let message: BridgeResponse;
    try {
      message = JSON.parse(line) as BridgeResponse;
    } catch {
      this.recentStderr = `${this.recentStderr}\n[bridge-stdout] ${line}`.slice(-4000);
      return;
    }

    if (message.event === "response") {
      const pending = this.pendingUnary.get(message.id);
      if (!pending) {
        return;
      }
      this.pendingUnary.delete(message.id);
      pending.resolve(message.payload);
      return;
    }

    if (message.event === "token") {
      this.pendingStreams.get(message.id)?.push(message.content ?? "");
      return;
    }

    if (message.event === "done") {
      this.pendingStreams.get(message.id)?.complete();
      return;
    }

    if (message.event === "error") {
      const error = new Error(message.content ?? "Unknown bridge error");
      const pendingUnary = this.pendingUnary.get(message.id);
      if (pendingUnary) {
        this.pendingUnary.delete(message.id);
        pendingUnary.reject(error);
      }
      this.pendingStreams.get(message.id)?.fail(error);
    }
  }

  private writeMessage(message: { id: string; command: BridgeCommand; payload: object }): void {
    if (!this.process) {
      throw new Error("Python bridge is not running");
    }
    this.process.stdin.write(`${JSON.stringify(message)}\n`);
  }

  private buildRequestId(): string {
    this.nextRequestId += 1;
    return `req-${this.nextRequestId}`;
  }

  private failAll(error: Error): void {
    for (const [requestId, pending] of this.pendingUnary) {
      this.pendingUnary.delete(requestId);
      pending.reject(error);
    }
    for (const [requestId, queue] of this.pendingStreams) {
      this.pendingStreams.delete(requestId);
      queue.fail(error);
    }
  }
}
