import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";

import type { CoordinatorGateway } from "../server.js";
import {
  LegacyQueryRequestSchema,
  TextQueryRequestSchema,
  UrlQueryRequestSchema,
  type QueryRequest,
} from "../types.js";

async function streamQuery(reply: FastifyReply, iterator: AsyncIterable<string>): Promise<FastifyReply> {
  let started = false;
  try {
    for await (const token of iterator) {
      if (!started) {
        reply.raw.setHeader("Content-Type", "text/plain; charset=utf-8");
        reply.raw.setHeader("Transfer-Encoding", "chunked");
        started = true;
      }
      reply.raw.write(token);
    }
    if (!started) {
      reply.raw.setHeader("Content-Type", "text/plain; charset=utf-8");
    }
    reply.raw.end();
    return reply;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Query stream failed";
    if (!started) {
      reply.status(500);
      return reply.send({ error: message });
    }
    reply.raw.write(`\n[stream-error] ${message}`);
    reply.raw.end();
    return reply;
  }
}

type MultipartRequest = FastifyRequest<{ Querystring: { session_id?: string } }> & {
  file(): Promise<{
    filename: string;
    mimetype: string;
    toBuffer(): Promise<Buffer>;
  } | undefined>;
};

export function registerQueryRoute(app: FastifyInstance, gateway: CoordinatorGateway): void {
  app.post("/query", async (request, reply) => {
    const parsed = LegacyQueryRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      reply.status(400);
      return { error: parsed.error.flatten() };
    }
    return streamQuery(reply, gateway.query(parsed.data));
  });

  app.post("/query/text", async (request, reply) => {
    const parsed = TextQueryRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      reply.status(400);
      return { error: parsed.error.flatten() };
    }
    return streamQuery(reply, gateway.query(parsed.data));
  });

  app.post("/query/url", async (request, reply) => {
    const parsed = UrlQueryRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      reply.status(400);
      return { error: parsed.error.flatten() };
    }
    return streamQuery(reply, gateway.query(parsed.data));
  });

  app.post("/query/file", async (request, reply) => {
    const multipartRequest = request as MultipartRequest;
    const upload = await multipartRequest.file();
    const sessionId = String(multipartRequest.query.session_id ?? "");
    if (!upload || !sessionId) {
      reply.status(400);
      return { error: "multipart file upload and session_id query param are required" };
    }
    const buffer = await upload.toBuffer();
    const payload: QueryRequest = {
      modality: "file",
      input_base64: buffer.toString("base64"),
      filename: upload.filename,
      mime_type: upload.mimetype,
      session_id: sessionId,
    };
    return streamQuery(reply, gateway.query(payload));
  });

  app.post("/query/voice", async (request, reply) => {
    const multipartRequest = request as MultipartRequest;
    const upload = await multipartRequest.file();
    const sessionId = String(multipartRequest.query.session_id ?? "");
    if (!upload || !sessionId) {
      reply.status(400);
      return { error: "multipart file upload and session_id query param are required" };
    }
    const buffer = await upload.toBuffer();
    const payload: QueryRequest = {
      modality: "voice",
      input_base64: buffer.toString("base64"),
      filename: upload.filename,
      mime_type: upload.mimetype,
      session_id: sessionId,
    };
    return streamQuery(reply, gateway.query(payload));
  });
}
