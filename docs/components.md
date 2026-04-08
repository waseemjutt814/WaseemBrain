# Components

## Runtime Core
`brain/runtime.py` is the orchestrator for the maintained runtime path.

It wires together:
- settings loading
- memory graph
- expert registry validation
- expert pool
- router client selection
- controlled internet access
- knowledge bootstrap
- health reporting

Key methods:
- `query()`
- `health()`
- `recall()`
- `experts()`
- `flush_session_traces()`
- `close()`

## Interface Layer
The interface lives under `interface/src/`.

Main pieces:
- `server.ts` boots Fastify, static assets, HTTP routes, and WebSocket routes
- `python_gateway.ts` keeps a long-lived Python bridge process and converts bridge messages into async streams
- `routes/*.ts` validate request and response shapes with Zod
- `ws/handler.ts` streams query responses to WebSocket clients

The interface contract is intentionally thin. It delegates business logic to the Python runtime instead of duplicating it in TypeScript. The structured assistant websocket plus `/api/catalog` and `/api/actions` are the maintained product contract.

## Coordinator
`brain/coordinator.py` handles the request pipeline after normalization.

At a high level it:
1. normalizes the incoming signal
2. gathers emotion and dialogue context
3. asks the router which experts are needed
4. recalls grounded memory when appropriate
5. invokes experts
6. assembles the final streamed response
7. records traces for knowledge-only learning

## Expert System
The expert subsystem is split across:
- `brain/experts/registry.py`
- `brain/experts/pool.py`
- `brain/experts/expert.py`
- `experts/base/`

Important behaviors:
- registry validation happens during runtime startup
- experts are loaded on demand from the declared registry
- the pool enforces `EXPERT_MAX_LOADED`
- idle eviction is available, with a background evictor only when an event loop is already running
- knowledge experts can load local module content without requiring an external model

## Memory Layer
The memory stack combines:
- `brain/memory/sqlite_store.py` for metadata, sessions, and graph edges
- `brain/memory/vector_store.py` for vector search
- `brain/memory/graph.py` for storage, recall, provenance, and decay workflows

Vector backends:
- native `hnswlib` when available
- portable JSON-backed HNSW-compatible fallback
- text-only SQLite fallback when explicitly requested

Recall ranking combines:
- semantic similarity
- recency
- session affinity
- provenance confidence

## Router Layer
Router clients live in `brain/router/client.py`.

Available modes:
- `ArtifactRouterClient` for the local routing artifact
- `RouterDaemonClient` for the optional gRPC daemon
- `HybridRouterClient` for daemon-first with artifact fallback

The default runtime contract remains local-first. The daemon is an accelerator, not a boot requirement.

## Knowledge And Learning
Knowledge and learning are deliberately scoped.

Core pieces:
- `brain/bootstrap.py` seeds built-in knowledge cards
- `brain/learning/policy.py` exports and reloads response policy artifacts
- `brain/learning/corrector.py` records session traces
- `scripts/evolve_knowledge.py` performs auditable knowledge maintenance and writes a report

Current boundary:
- learning is enabled for traces, policy refresh, and memory maintenance
- self-improvement is knowledge-only
- the learning loop does not autonomously edit repo code

## Assistant Actions`r`nThe protected assistant action surface lives in `brain/assistant/actions.py` and is exposed through `/api/actions` and `/ws/assistant`.`r`n`r`nCurrent maintained action families include:`r`n- workspace inspection and repo search`r`n- runtime health and daemon control`r`n- verification/report execution`r`n- Docker smoke verification`r`n- explicit-preview firewall operations`r`n`r`n## Reporting And Metadata
Two small maintenance scripts keep the repo honest:
- `scripts/sync_workspace_metadata.py` mirrors Python metadata into `package.json`
- `scripts/project_report.py` writes repo inventory, assistant-surface readiness, Docker smoke status, and verification summaries into `logs/`