import type { FastifyInstance } from "fastify";

import type { CoordinatorGateway } from "../server.js";
import { ExpertsStatusSchema } from "../types.js";

export function registerExpertsRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.get("/experts", async (_request, reply) => {
    const result = await gateway.experts();
    const parsed = ExpertsStatusSchema.safeParse(result);
    if (!parsed.success) {
      reply.status(500);
      return { error: parsed.error.flatten() };
    }
    return parsed.data;
  });
}
