import type { FastifyInstance } from "fastify";

import type { CoordinatorGateway } from "../server.js";
import { HealthResponseSchema, type HealthResponse } from "../types.js";

function normalizeHealthResponse(payload: HealthResponse | Record<string, unknown>): HealthResponse {
  const currentPayload = payload as Record<string, unknown>;
  const currentCapabilities = (currentPayload.capabilities ?? {}) as Record<string, unknown>;
  const currentProvider = (currentPayload.provider ?? {}) as Record<string, unknown>;
  const currentRealtimeVoice = (currentPayload.realtime_voice ?? {}) as Record<string, unknown>;
  const currentAutomation = (currentPayload.automation ?? {}) as Record<string, unknown>;

  return {
    ...(currentPayload as unknown as HealthResponse),
    capabilities: {
      model_free_core:
        typeof currentCapabilities.model_free_core === "boolean" ? currentCapabilities.model_free_core : true,
      api_key_required:
        typeof currentCapabilities.api_key_required === "boolean" ? currentCapabilities.api_key_required : false,
      self_improvement_scope:
        typeof currentCapabilities.self_improvement_scope === "string" ? currentCapabilities.self_improvement_scope : "knowledge-only",
      router_acceleration_optional:
        typeof currentCapabilities.router_acceleration_optional === "boolean" ? currentCapabilities.router_acceleration_optional : true,
      default_router_backend:
        typeof currentCapabilities.default_router_backend === "string"
          ? currentCapabilities.default_router_backend
          : String(currentPayload.router_backend ?? "local"),
    },
    assistant_mode:
      typeof currentPayload.assistant_mode === "string" ? currentPayload.assistant_mode : "local",
    provider: {
      configured: typeof currentProvider.configured === "boolean" ? currentProvider.configured : false,
      mode: currentProvider.mode === "openai_compatible" ? "openai_compatible" : "local_grounded",
      model: typeof currentProvider.model === "string" ? currentProvider.model : "local-grounded",
      reachable: typeof currentProvider.reachable === "boolean" ? currentProvider.reachable : false,
    },
    realtime_voice: {
      supported: typeof currentRealtimeVoice.supported === "boolean" ? currentRealtimeVoice.supported : true,
      mode: typeof currentRealtimeVoice.mode === "string" ? currentRealtimeVoice.mode : "turn-based",
    },
    automation: {
      approval_required:
        typeof currentAutomation.approval_required === "boolean" ? currentAutomation.approval_required : true,
      audit_enabled: typeof currentAutomation.audit_enabled === "boolean" ? currentAutomation.audit_enabled : true,
    },
  };
}

export function registerHealthRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.get("/health", async (_request, reply) => {
    const result = normalizeHealthResponse(await gateway.health());
    const parsed = HealthResponseSchema.safeParse(result);
    if (!parsed.success) {
      reply.status(500);
      return { error: parsed.error.flatten() };
    }
    return parsed.data;
  });
}
