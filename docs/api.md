# API Reference

## Interface Server
The TypeScript server exposes HTTP and WebSocket routes through Fastify in `interface/src/server.ts`.

Static UI:
- `GET /`
- `GET /chat.html`

Service routes:
- `GET /health`
- `GET /experts`
- `GET /memory/recall?q=...`
- `POST /query`
- `POST /query/text`
- `POST /query/url`
- `POST /query/file?session_id=...`
- `POST /query/voice?session_id=...`
- `GET /ws`

## Query Endpoints
All HTTP query routes stream plain-text tokens back to the caller.

### Legacy Text Query
`POST /query`

```json
{
  "input": "Explain the latest memory snapshot",
  "modality": "text",
  "session_id": "session-123"
}
```

### Typed Text Query
`POST /query/text`

```json
{
  "modality": "text",
  "input": "Summarize the system health",
  "session_id": "session-123"
}
```

### URL Query
`POST /query/url`

```json
{
  "modality": "url",
  "url": "https://example.com",
  "session_id": "session-123"
}
```

### File And Voice Uploads
`POST /query/file` and `POST /query/voice` accept multipart uploads and require a `session_id` query parameter.

The server converts the upload into a typed payload with:
- `modality`
- `input_base64`
- `filename`
- `mime_type`
- `session_id`

## WebSocket Streaming
`GET /ws`

Accepted request shapes:
- text query payloads
- URL query payloads

Returned stream messages:

```json
{
  "type": "token",
  "content": "partial text"
}
```

Other message types are `done` and `error`.

## Health Response
`GET /health`

The runtime always returns `status: "ok"` for a valid response. Readiness is expressed through:
- `condition`
- `condition_summary`
- `ready`

Important health fields:
- `experts_loaded`
- `experts_available`
- `router_backend`
- `vector_backend`
- `components`
- `capabilities`
- `learning`
- `knowledge`
- `router`
- `storage`

Example shape:

```json
{
  "status": "ok",
  "project_name": "Waseem Brain",
  "condition": "ready",
  "condition_summary": "response policy still in rule-default mode",
  "ready": true,
  "router_backend": "local",
  "vector_backend": "portable-hnsw",
  "capabilities": {
    "model_free_core": true,
    "api_key_required": false,
    "self_improvement_scope": "knowledge-only",
    "router_acceleration_optional": true,
    "default_router_backend": "local"
  }
}
```

## Experts Route
`GET /experts`

```json
{
  "loaded": ["language-expert", "code-expert"],
  "count": 2
}
```

## Memory Recall Route
`GET /memory/recall?q=router`

Returns an array of memory summaries:

```json
[
  {
    "id": "mem-123",
    "content": "Router artifact was refreshed",
    "confidence": 0.81,
    "source": "auto-reflection-loop"
  }
]
```

## Python Runtime Surface
The main Python entry point is `brain/runtime.py`.

Primary methods:
- `query(raw_input, modality_hint, session_id)`
- `health()`
- `recall(query, limit=5)`
- `experts()`
- `flush_session_traces(session_id)`
- `close()`

The runtime composes settings, registry validation, expert loading, memory recall, controlled internet access, knowledge bootstrapping, and health reporting.

## Structured Assistant Session
GET /ws/assistant is the primary assistant contract for chat, URL grounding, file analysis, voice turns, proof events, approval-required actions, and explicit action confirmations.
