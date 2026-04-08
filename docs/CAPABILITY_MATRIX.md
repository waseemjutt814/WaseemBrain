# Capability Matrix

## Guaranteed Core
- Offline-first routing and response assembly
- Typed expert loading and registry validation
- SQLite-backed memory metadata
- HNSW-compatible vector index with portable fallback implementation
- WebSocket and HTTP query streaming through the Python bridge
- Knowledge-only self-improvement via traces, response policy refresh, and memory maintenance

## Optional Accelerators
- gRPC router daemon
- Rust router build and test flow
- Native `hnswlib` backend when available

## Explicit Non-Goals
- Hidden local LLM fallback in the default runtime path
- Autonomous repo code editing by the learning loop
- API-key-dependent core behavior
