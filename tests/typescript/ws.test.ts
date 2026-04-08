import test from "node:test";
import assert from "node:assert/strict";
import { once } from "node:events";

import WebSocket from "ws";

import { createServer } from "../../interface/src/server.js";
import type { AssistantServerEvent } from "../../interface/src/types.js";
import { streamToSocket } from "../../interface/src/ws/stream.js";

const healthPayload = {
  status: "ok" as const,
  project_name: "Waseem Brain",
  condition: "ready" as const,
  condition_summary: "response policy still in rule-default mode",
  ready: true,
  experts_loaded: 0,
  experts_available: 3,
  expert_ids: ["language-en", "code-general", "geography"],
  memory_node_count: 0,
  uptime_sec: 0,
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

test("streamToSocket sends token and done messages", async () => {
  const sent: string[] = [];
  const socket = {
    send(message: string) {
      sent.push(message);
    },
  };

  async function* iterator(): AsyncIterable<string> {
    yield "hello";
  }

  await streamToSocket(socket, iterator());
  assert.equal(sent.length, 2);
});

test("streamToSocket sends error messages on failure", async () => {
  const sent: string[] = [];
  const socket = {
    send(message: string) {
      sent.push(message);
    },
  };

  async function* iterator(): AsyncIterable<string> {
    yield "hello";
    throw new Error("stream exploded");
  }

  await streamToSocket(socket, iterator());
  assert.equal(sent.length, 2);
  const errorPayload = JSON.parse(sent[1]) as { type: string; content: string };
  assert.equal(errorPayload.type, "error");
  assert.match(errorPayload.content, /stream exploded/);
});

test("websocket route streams token and done messages", async () => {
  const app = createServer({
    async *query(): AsyncIterable<string> {
      yield "hello ";
      yield "world ";
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

  await app.listen({ port: 0, host: "127.0.0.1" });
  const address = app.server.address();
  assert.ok(address && typeof address === "object");
  const socket = new WebSocket(`ws://127.0.0.1:${address.port}/ws`);

  try {
    await once(socket, "open");
    const messages: Array<{ type: string; content: string }> = [];
    socket.on("message", (payload: WebSocket.RawData) => {
      messages.push(JSON.parse(payload.toString("utf-8")) as { type: string; content: string });
    });
    socket.send(JSON.stringify({ input: "hello", modality: "text", session_id: "ws-1" }));

    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("timed out waiting for done message")), 5000);
      const check = setInterval(() => {
        if (messages.some((message) => message.type === "done")) {
          clearTimeout(timer);
          clearInterval(check);
          resolve();
        }
      }, 20);
    });

    assert.deepEqual(
      messages.map((message) => message.type),
      ["token", "token", "done"],
    );
    assert.equal(messages[0].content, "hello ");
    assert.equal(messages[1].content, "world ");
  } finally {
    socket.close();
    await app.close();
  }
});

test("websocket route returns an error on invalid json", async () => {
  const app = createServer({
    async *query(): AsyncIterable<string> {
      yield "unused";
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

  await app.listen({ port: 0, host: "127.0.0.1" });
  const address = app.server.address();
  assert.ok(address && typeof address === "object");
  const socket = new WebSocket(`ws://127.0.0.1:${address.port}/ws`);

  try {
    await once(socket, "open");
    socket.send("{not-json");
    const [payload] = (await once(socket, "message")) as [WebSocket.RawData];
    const parsed = JSON.parse(payload.toString("utf-8")) as { type: string; content: string };
    assert.equal(parsed.type, "error");
    assert.match(parsed.content.toLowerCase(), /json/);
  } finally {
    socket.close();
    await app.close();
  }
});

test("assistant websocket streams structured assistant events", async () => {
  const app = createServer({
    async *query(): AsyncIterable<string> {
      yield "unused";
    },
    async *assistant(): AsyncIterable<AssistantServerEvent> {
      yield { type: "status", content: "Assistant mode: conversational answer path.", route: "general_chat" };
      yield {
        type: "message.done",
        content: "Hello from assistant.",
        route: "general_chat",
        metadata: {
          route: "general_chat",
          provider: { configured: false, mode: "local_grounded", model: "local-grounded", reachable: true },
          tools: ["local-grounded"],
          citations_count: 0,
          render_strategy: "direct",
          transcript: "",
          local_mode: true,
        },
      };
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
    async actions() {
      return { groups: [] };
    },
  });

  await app.listen({ port: 0, host: "127.0.0.1" });
  const address = app.server.address();
  assert.ok(address && typeof address === "object");
  const socket = new WebSocket(`ws://127.0.0.1:${address.port}/ws/assistant`);

  try {
    await once(socket, "open");
    const messages: Array<{ type: string; content?: string; metadata?: { local_mode: boolean } }> = [];
    socket.on("message", (payload: WebSocket.RawData) => {
      messages.push(JSON.parse(payload.toString("utf-8")) as { type: string; content?: string; metadata?: { local_mode: boolean } });
    });
    socket.send(JSON.stringify({ type: "chat.submit", session_id: "assistant-ws-1", modality: "text", input: "hello" }));

    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("timed out waiting for assistant done event")), 5000);
      const check = setInterval(() => {
        if (messages.some((message) => message.type === "message.done")) {
          clearTimeout(timer);
          clearInterval(check);
          resolve();
        }
      }, 20);
    });

    assert.deepEqual(
      messages.map((message) => message.type),
      ["status", "message.done"],
    );
    assert.equal(messages[1]?.content, "Hello from assistant.");
    assert.equal(messages[1]?.metadata?.local_mode, true);
  } finally {
    socket.close();
    await app.close();
  }
});

test("assistant websocket rejects action preview on compatibility fallback", async () => {
  const app = createServer({
    async *query(): AsyncIterable<string> {
      yield "unused";
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
    async actions() {
      return { groups: [] };
    },
  });

  await app.listen({ port: 0, host: "127.0.0.1" });
  const address = app.server.address();
  assert.ok(address && typeof address === "object");
  const socket = new WebSocket(`ws://127.0.0.1:${address.port}/ws/assistant`);

  try {
    await once(socket, "open");
    socket.send(JSON.stringify({ type: "action.preview", session_id: "assistant-ws-2", action_id: "system.runtime.status", inputs: {} }));
    const [payload] = (await once(socket, "message")) as [WebSocket.RawData];
    const parsed = JSON.parse(payload.toString("utf-8")) as { type: string; content: string };
    assert.equal(parsed.type, "error");
    assert.match(parsed.content, /action\.preview/);
  } finally {
    socket.close();
    await app.close();
  }
});

