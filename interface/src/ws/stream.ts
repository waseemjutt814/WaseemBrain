import type WebSocket from "ws";

import type { StreamMessage } from "../types.js";

type SocketLike = Pick<WebSocket, "send">;

export async function streamToSocket(socket: SocketLike, iterator: AsyncIterable<string>): Promise<void> {
  try {
    for await (const token of iterator) {
      const message: StreamMessage = { type: "token", content: token };
      socket.send(JSON.stringify(message));
    }
    const doneMessage: StreamMessage = { type: "done", content: "" };
    socket.send(JSON.stringify(doneMessage));
  } catch (error) {
    const message: StreamMessage = {
      type: "error",
      content: error instanceof Error ? error.message : "Stream failed",
    };
    socket.send(JSON.stringify(message));
  }
}
