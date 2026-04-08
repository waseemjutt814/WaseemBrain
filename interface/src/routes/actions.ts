import type { FastifyInstance } from "fastify";

import type { CoordinatorGateway } from "../server.js";
import { ActionCatalogSchema } from "../types.js";

export function registerActionsRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.get("/api/actions", async (_request, reply) => {
    const result = typeof gateway.actions === "function" ? await gateway.actions() : { groups: [] };
    const parsed = ActionCatalogSchema.safeParse(result);
    if (!parsed.success) {
      reply.status(500);
      return { error: parsed.error.flatten() };
    }
    return parsed.data;
  });
}
