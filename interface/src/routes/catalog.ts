import type { FastifyInstance } from "fastify";

import type { CoordinatorGateway } from "../server.js";
import { IntegrationCatalogSchema } from "../types.js";

export function registerCatalogRoute(app: FastifyInstance, _gateway: CoordinatorGateway): void {
  app.get("/api/catalog", async (_request, reply) => {
    const apiHost = (process.env.API_HOST ?? "127.0.0.1").trim().toLowerCase();
    const localOnlyDefault = apiHost === "127.0.0.1" || apiHost === "localhost";

    const result = {
      project_name: "Waseem Brain",
      api_style: "custom-rest-and-ws",
      auth: "none by default",
      local_only_default: localOnlyDefault,
      openai_compatible: false,
      websocket_path: "/ws",
      default_surface: "assistant",
      conversation_modes: ["general_chat", "coding", "repo_work", "grounded_answer", "web_lookup", "system_action"],
      voice_modes: ["turn-based", "browser-tts"],
      structured_session_ws_path: "/ws/assistant",
      notes: [
        "Chat, voice, and actions use the structured assistant websocket by default.",
        "Compatibility REST routes remain available for text, URL, file, and voice submissions.",
        "System changes require preview plus explicit confirmation before execution.",
        "The local action surface covers workspace inspection, verification gates, runtime daemon control, and Docker smoke checks.",
        "If another tool only supports OpenAI-style providers, place a compatibility adapter in front of this API.",
      ],
      endpoints: [
        {
          id: "health",
          method: "GET",
          path: "/health",
          summary: "Runtime condition, provider state, automation posture, router state, memory, and learning snapshot.",
          request_format: "none",
          response_format: "json",
        },
        {
          id: "actions",
          method: "GET",
          path: "/api/actions",
          summary: "Discoverable action catalog for assistant, terminal, and protected system operations.",
          request_format: "none",
          response_format: "json",
        },
        {
          id: "catalog",
          method: "GET",
          path: "/api/catalog",
          summary: "Assistant surface, conversation modes, voice modes, and integration profile.",
          request_format: "none",
          response_format: "json",
        },
        {
          id: "query-text",
          method: "POST",
          path: "/query/text",
          summary: "Compatibility text chat endpoint backed by the assistant orchestrator.",
          request_format: "application/json",
          response_format: "streamed text",
        },
        {
          id: "query-url",
          method: "POST",
          path: "/query/url",
          summary: "Compatibility URL analysis endpoint.",
          request_format: "application/json",
          response_format: "streamed text",
        },
        {
          id: "query-file",
          method: "POST",
          path: "/query/file?session_id=...",
          summary: "Compatibility document upload endpoint.",
          request_format: "multipart/form-data",
          response_format: "streamed text",
        },
        {
          id: "query-voice",
          method: "POST",
          path: "/query/voice?session_id=...",
          summary: "Compatibility voice upload endpoint.",
          request_format: "multipart/form-data",
          response_format: "streamed text",
        },
        {
          id: "assistant-ws",
          method: "WS",
          path: "/ws/assistant",
          summary: "Primary structured assistant session for chat, live voice turns, proof events, and protected actions.",
          request_format: "json messages",
          response_format: "json event stream",
        },
        {
          id: "ws",
          method: "WS",
          path: "/ws",
          summary: "Compatibility stream for text and URL messages over WebSocket.",
          request_format: "json messages",
          response_format: "json token events",
        },
      ],
    };

    const parsed = IntegrationCatalogSchema.safeParse(result);
    if (!parsed.success) {
      reply.status(500);
      return { error: parsed.error.flatten() };
    }
    return parsed.data;
  });
}
