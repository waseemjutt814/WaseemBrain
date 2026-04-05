import type { FastifyInstance } from "fastify";

import type { CoordinatorGateway } from "../server.js";
import { HealthResponseSchema } from "../types.js";

export function registerHealthRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.get("/health", async (_request, reply) => {
    const result = await gateway.health();
    const parsed = HealthResponseSchema.safeParse(result);
    if (!parsed.success) {
      reply.status(500);
      return { error: parsed.error.flatten() };
    }
    return parsed.data;
  });
}
