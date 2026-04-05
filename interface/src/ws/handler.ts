import type { FastifyInstance } from "fastify";
import type WebSocket from "ws";

import type { CoordinatorGateway } from "../server.js";
import { WsQueryRequestSchema, type StreamMessage } from "../types.js";
import { streamToSocket } from "./stream.js";

export function registerWebsocketRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.get("/ws", { websocket: true }, (socket: WebSocket) => {
    socket.on("message", async (payload: WebSocket.RawData) => {
      let rawMessage: unknown;
      try {
        rawMessage = JSON.parse(payload.toString("utf-8"));
      } catch (error) {
        const errorMessage: StreamMessage = {
          type: "error",
          content: error instanceof Error ? error.message : "Invalid JSON payload",
        };
        socket.send(JSON.stringify(errorMessage));
        return;
      }
      const decoded = WsQueryRequestSchema.safeParse(rawMessage);
      if (!decoded.success) {
        const errorMessage: StreamMessage = { type: "error", content: decoded.error.message };
        socket.send(JSON.stringify(errorMessage));
        return;
      }
      await streamToSocket(socket, gateway.query(decoded.data));
    });
  });
}
