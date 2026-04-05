# Interface Bridge

## Purpose
Maintain the Fastify surface and concurrent Python bridge that expose the offline chat and coding brain over HTTP and WebSocket.

## Focus Files
- `interface/src/server.ts`
- `interface/src/routes/`
- `interface/src/ws/`
- `interface/src/python_gateway.ts`
- `scripts/coordinator_bridge.py`

## Rules
- `POST /query` stays as the text compatibility alias.
- Text, file, and voice are the primary staged routes; no hidden internet dependency should appear in the request path.
- WebSocket streaming should remain first-class for long text and code tasks.
- Bridge work must be concurrent, cancellable, and health/metadata requests must not queue behind long queries.

## Checks
- `npm run build`
- `npm test`
