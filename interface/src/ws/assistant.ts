import type { FastifyInstance } from "fastify";
import type WebSocket from "ws";

import type { CoordinatorGateway } from "../server.js";
import {
  AssistantClientEventSchema,
  type AssistantClientEvent,
  type AssistantServerEvent,
  type QueryRequest,
} from "../types.js";

function sendEvent(socket: WebSocket, event: AssistantServerEvent): void {
  socket.send(JSON.stringify(event));
}

async function streamFallback(socket: WebSocket, gateway: CoordinatorGateway, message: AssistantClientEvent): Promise<void> {
  if (message.type === "action.preview") {
    sendEvent(socket, { type: "error", content: "Compatibility assistant fallback cannot process \"action.preview\" requests." });
    return;
  }
  if (message.type === "action.confirm") {
    sendEvent(socket, { type: "error", content: "Compatibility assistant fallback cannot process \"action.confirm\" requests." });
    return;
  }
  if (message.type === "session.update") {
    sendEvent(socket, { type: "status", content: "Compatibility assistant fallback is active.", route: "general_chat" });
    return;
  }
  if (message.type !== "chat.submit") {
    sendEvent(socket, { type: "error", content: "This gateway does not support structured assistant actions or live voice yet." });
    return;
  }
  const modality = message.modality ?? "text";
  if (modality === "file") {
    sendEvent(socket, { type: "error", content: "File assistant mode requires the structured runtime gateway." });
    return;
  }
  const queryPayload: QueryRequest = modality === "url"
    ? { modality: "url", url: message.input ?? "", session_id: message.session_id }
    : { modality: "text", input: message.input ?? "", session_id: message.session_id };
  sendEvent(socket, { type: "status", content: "Compatibility assistant fallback is active.", route: "general_chat" });
  for await (const token of gateway.query(queryPayload)) {
    sendEvent(socket, { type: "message.delta", content: token, route: "general_chat" });
  }
  sendEvent(socket, {
    type: "message.done",
    content: "",
    route: "general_chat",
    metadata: {
      route: "general_chat",
      provider: { configured: false, mode: "local_grounded", model: "compatibility", reachable: true },
      tools: ["compatibility-query"],
      citations_count: 0,
      render_strategy: "direct",
      transcript: "",
      local_mode: true,
    },
  });
}

export function registerAssistantWebsocketRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.get("/ws/assistant", { websocket: true }, (socket: WebSocket) => {
    let voiceSessionId = "";
    const voiceChunks: string[] = [];

    socket.on("message", async (payload: WebSocket.RawData) => {
      let rawMessage: unknown;
      try {
        rawMessage = JSON.parse(payload.toString("utf-8"));
      } catch (error) {
        sendEvent(socket, { type: "error", content: error instanceof Error ? error.message : "Invalid JSON payload" });
        return;
      }
      const decoded = AssistantClientEventSchema.safeParse(rawMessage);
      if (!decoded.success) {
        sendEvent(socket, { type: "error", content: decoded.error.message });
        return;
      }
      if (decoded.data.type === "voice.start") {
        voiceSessionId = decoded.data.session_id;
        voiceChunks.length = 0;
        sendEvent(socket, { type: "status", content: "Voice capture started.", route: "grounded_answer" });
        return;
      }
      if (decoded.data.type === "voice.chunk") {
        if (voiceSessionId !== decoded.data.session_id) {
          sendEvent(socket, { type: "error", content: "Voice chunk session mismatch." });
          return;
        }
        voiceChunks.push(decoded.data.chunk_base64);
        return;
      }

      let assistantRequest: AssistantClientEvent | Record<string, unknown> = decoded.data;
      if (decoded.data.type === "voice.stop") {
        assistantRequest = {
          type: "voice.stop",
          session_id: decoded.data.session_id,
          filename: decoded.data.filename,
          mime_type: decoded.data.mime_type,
          input_base64: voiceChunks.join(""),
        };
      }

      try {
        if (typeof gateway.assistant === "function") {
          for await (const event of gateway.assistant(assistantRequest as AssistantClientEvent)) {
            sendEvent(socket, event);
          }
          return;
        }
        await streamFallback(socket, gateway, assistantRequest as AssistantClientEvent);
      } catch (error) {
        sendEvent(socket, { type: "error", content: error instanceof Error ? error.message : "Assistant session failed" });
      }
    });
  });
}
