import type { FastifyInstance } from "fastify";

import type { CoordinatorGateway } from "../server.js";
import { MemoryRecallResponseSchema } from "../types.js";

export function registerMemoryRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.get("/memory/recall", async (request, reply) => {
    const query = String((request.query as { q?: string }).q ?? "");
    const result = await gateway.recall(query);
    const parsed = MemoryRecallResponseSchema.safeParse(result);
    if (!parsed.success) {
      reply.status(500);
      return { error: parsed.error.flatten() };
    }
    return parsed.data;
  });
}
