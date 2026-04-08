import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
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

type BridgeCommand = "query" | "health" | "recall" | "experts" | "actions" | "assistant" | "shutdown";

type BridgeResponse = {
  id: string;
  event: "response" | "token" | "done" | "error" | "assistant";
  payload?: unknown;
  content?: string;
};

type PendingUnary = {
  resolve(value: unknown): void;
  reject(error: Error): void;
  timestamp: number;
};

type PythonCoordinatorGatewayOptions = {
  pythonExecutable?: string;
  bridgePath?: string;
  cwd?: string;
  env?: NodeJS.ProcessEnv;
  maxPendingRequests?: number;
  maxPendingStreams?: number;
  requestTimeoutMs?: number;
};

// Resource limits
const DEFAULT_MAX_PENDING_REQUESTS = 100;
const DEFAULT_MAX_PENDING_STREAMS = 50;
const DEFAULT_REQUEST_TIMEOUT_MS = 60000; // 60 seconds
const STALE_REQUEST_THRESHOLD_MS = 120000; // 2 minutes

class AsyncTokenQueue<T> implements AsyncIterable<T>, AsyncIterator<T> {
  private items: T[] = [];
  private waiters: Array<(value: IteratorResult<T>) => void> = [];
  private failure: Error | null = null;
  private finished = false;

  push(value: T): void {
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

  async next(): Promise<IteratorResult<T>> {
    if (this.items.length > 0) {
      return { value: this.items.shift()!, done: false };
    }
    if (this.failure) {
      throw this.failure;
    }
    if (this.finished) {
      return { value: undefined, done: true };
    }
    return await new Promise<IteratorResult<T>>((resolve) => {
      this.waiters.push(resolve);
    });
  }

  [Symbol.asyncIterator](): AsyncIterator<T> {
    return this;
  }
}

export class PythonCoordinatorGateway {
  private readonly options: Required<Pick<PythonCoordinatorGatewayOptions, 'maxPendingRequests' | 'maxPendingStreams' | 'requestTimeoutMs'>> & PythonCoordinatorGatewayOptions;
  private process: ChildProcessWithoutNullStreams | null = null;
  private readonly pendingUnary = new Map<string, PendingUnary>();
  private readonly pendingTokenStreams = new Map<string, AsyncTokenQueue<string>>();
  private readonly pendingAssistantStreams = new Map<string, AsyncTokenQueue<AssistantServerEvent>>();
  private readonly requestDeduplication = new Map<string, Promise<unknown>>();
  private nextRequestId = 0;
  private recentStderr = "";
  private closing = false;
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor(options: PythonCoordinatorGatewayOptions = {}) {
    this.options = {
      ...options,
      maxPendingRequests: options.maxPendingRequests ?? DEFAULT_MAX_PENDING_REQUESTS,
      maxPendingStreams: options.maxPendingStreams ?? DEFAULT_MAX_PENDING_STREAMS,
      requestTimeoutMs: options.requestTimeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS,
    };
    // Start periodic cleanup of stale requests
    this.cleanupInterval = setInterval(() => this.cleanupStaleRequests(), 30000);
  }

  async *query(request: QueryRequest): AsyncIterable<string> {
    const requestId = this.sendStreamingRequest("query", request, "token");
    const queue = this.pendingTokenStreams.get(requestId);
    if (!queue) {
      throw new Error("Bridge token stream was not initialized");
    }
    try {
      for await (const token of queue) {
        yield token;
      }
    } finally {
      this.pendingTokenStreams.delete(requestId);
    }
  }

  async *assistant(request: AssistantClientEvent): AsyncIterable<AssistantServerEvent> {
    const requestId = this.sendStreamingRequest("assistant", request, "assistant");
    const queue = this.pendingAssistantStreams.get(requestId);
    if (!queue) {
      throw new Error("Bridge assistant stream was not initialized");
    }
    try {
      for await (const event of queue) {
        yield event;
      }
    } finally {
      this.pendingAssistantStreams.delete(requestId);
    }
  }

  async health(): Promise<HealthResponse> {
    return this.sendUnaryRequest<HealthResponse>("health", {}, true);
  }

  async recall(query: string): Promise<MemoryNodeSummary[]> {
    // Deduplicate recall requests for same query
    const dedupeKey = `recall:${query}`;
    return this.sendUnaryRequest<MemoryNodeSummary[]>("recall", { query, limit: 5 }, true, dedupeKey);
  }

  async experts(): Promise<ExpertsStatus> {
    return this.sendUnaryRequest<ExpertsStatus>("experts", {}, true);
  }

  async actions(): Promise<ActionCatalog> {
    return this.sendUnaryRequest<ActionCatalog>("actions", {}, true);
  }

  async close(): Promise<void> {
    // Stop cleanup interval
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    
    const child = this.process;
    if (!child) {
      return;
    }
    this.closing = true;

    // Fail all pending requests with shutdown error
    const shutdownError = new Error("Gateway is shutting down");
    this.failAll(shutdownError);
    
    // Clear deduplication cache
    this.requestDeduplication.clear();

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
    
    this.process = null;
  }
  
  /**
   * Get current resource usage statistics.
   */
  getResourceStats(): {
    pendingUnary: number;
    pendingTokenStreams: number;
    pendingAssistantStreams: number;
    maxPendingRequests: number;
    maxPendingStreams: number;
  } {
    return {
      pendingUnary: this.pendingUnary.size,
      pendingTokenStreams: this.pendingTokenStreams.size,
      pendingAssistantStreams: this.pendingAssistantStreams.size,
      maxPendingRequests: this.options.maxPendingRequests,
      maxPendingStreams: this.options.maxPendingStreams,
    };
  }

  private sendStreamingRequest(command: BridgeCommand, payload: object, streamKind: "token" | "assistant"): string {
    this.ensureProcess();
    
    // Check resource limits
    const currentStreams = this.pendingTokenStreams.size + this.pendingAssistantStreams.size;
    if (currentStreams >= this.options.maxPendingStreams) {
      throw new Error(`Maximum pending streams (${this.options.maxPendingStreams}) exceeded. Consider waiting for existing requests to complete.`);
    }
    
    const requestId = this.buildRequestId();
    if (streamKind === "token") {
      this.pendingTokenStreams.set(requestId, new AsyncTokenQueue<string>());
    } else {
      this.pendingAssistantStreams.set(requestId, new AsyncTokenQueue<AssistantServerEvent>());
    }
    this.writeMessage({ id: requestId, command, payload });
    return requestId;
  }

  private async sendUnaryRequest<T>(
    command: Exclude<BridgeCommand, "query" | "assistant" | "shutdown">,
    payload: object,
    checkResources = false,
    dedupeKey?: string,
  ): Promise<T> {
    // Check deduplication
    if (dedupeKey) {
      const existing = this.requestDeduplication.get(dedupeKey);
      if (existing) {
        return existing as Promise<T>;
      }
    }
    
    this.ensureProcess();
    
    // Check resource limits
    if (checkResources && this.pendingUnary.size >= this.options.maxPendingRequests) {
      throw new Error(`Maximum pending requests (${this.options.maxPendingRequests}) exceeded. Consider waiting for existing requests to complete.`);
    }
    
    const requestId = this.buildRequestId();
    const promise = new Promise<T>((resolve, reject) => {
      // Add timeout
      const timeoutId = setTimeout(() => {
        this.pendingUnary.delete(requestId);
        if (dedupeKey) {
          this.requestDeduplication.delete(dedupeKey);
        }
        reject(new Error(`Request ${requestId} timed out after ${this.options.requestTimeoutMs}ms`));
      }, this.options.requestTimeoutMs);
      
      this.pendingUnary.set(requestId, {
        resolve: (value: unknown) => {
          clearTimeout(timeoutId);
          resolve(value as T);
        },
        reject: (error: Error) => {
          clearTimeout(timeoutId);
          reject(error);
        },
        timestamp: Date.now(),
      });
    });
    
    // Store for deduplication
    if (dedupeKey) {
      this.requestDeduplication.set(dedupeKey, promise);
      // Clean up dedupe cache after resolution
      promise.finally(() => {
        this.requestDeduplication.delete(dedupeKey);
      });
    }
    
    this.writeMessage({ id: requestId, command, payload });
    return promise;
  }

  private ensureProcess(): void {
    if (this.process) {
      return;
    }

    const isWin = process.platform === "win32";
    const customExecutable = this.options.pythonExecutable ?? process.env.PYTHON_EXECUTABLE;
    const pythonExecutable = customExecutable ?? (isWin ? "py" : "python3");
    const bridgePath = this.options.bridgePath ?? path.resolve(this.options.cwd ?? process.cwd(), "scripts", "coordinator_bridge.py");
    const runArgs = isWin && !customExecutable ? ["-3.11", bridgePath] : [bridgePath];

    const child = spawn(pythonExecutable, runArgs, {
      cwd: this.options.cwd ?? process.cwd(),
      env: {
        ...process.env,
        ...this.options.env,
        PYTHONUNBUFFERED: "1",
      },
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
      const error = new Error(`Python bridge exited unexpectedly (code=${code ?? "null"}, signal=${signal ?? "null"})${suffix}`);
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
      this.pendingTokenStreams.get(message.id)?.push(message.content ?? "");
      return;
    }

    if (message.event === "assistant") {
      this.pendingAssistantStreams.get(message.id)?.push(message.payload as AssistantServerEvent);
      return;
    }

    if (message.event === "done") {
      this.pendingTokenStreams.get(message.id)?.complete();
      this.pendingAssistantStreams.get(message.id)?.complete();
      return;
    }

    if (message.event === "error") {
      const error = new Error(message.content ?? "Bridge request failed");
      const unary = this.pendingUnary.get(message.id);
      if (unary) {
        this.pendingUnary.delete(message.id);
        unary.reject(error);
      }
      this.pendingTokenStreams.get(message.id)?.fail(error);
      this.pendingAssistantStreams.get(message.id)?.fail(error);
    }
  }

  private writeMessage(message: { id: string; command: BridgeCommand; payload: object }): void {
    if (!this.process) {
      throw new Error("Python bridge process is not running");
    }
    this.process.stdin.write(`${JSON.stringify(message)}\n`, "utf8");
  }

  private failAll(error: Error): void {
    for (const pending of this.pendingUnary.values()) {
      pending.reject(error);
    }
    this.pendingUnary.clear();
    for (const queue of this.pendingTokenStreams.values()) {
      queue.fail(error);
    }
    this.pendingTokenStreams.clear();
    for (const queue of this.pendingAssistantStreams.values()) {
      queue.fail(error);
    }
    this.pendingAssistantStreams.clear();
    this.requestDeduplication.clear();
  }
  
  /**
   * Cleanup stale requests that have been pending for too long.
   */
  private cleanupStaleRequests(): void {
    const now = Date.now();
    const staleThreshold = STALE_REQUEST_THRESHOLD_MS;
    
    // Cleanup stale unary requests
    for (const [id, pending] of this.pendingUnary.entries()) {
      if (now - pending.timestamp > staleThreshold) {
        this.pendingUnary.delete(id);
        pending.reject(new Error(`Request ${id} was cleaned up as stale after ${staleThreshold}ms`));
      }
    }
    
    // Note: Streams are cleaned up when they complete or fail
    // We don't auto-cleanup streams as they may be long-running
  }

  private buildRequestId(): string {
    this.nextRequestId += 1;
    return `python-bridge-${this.nextRequestId}`;
  }
}
