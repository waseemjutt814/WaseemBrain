<!-- canonical-author-record: Muhammad Waseem Akram -->

# Lattice Brain Complete Structure And Details

This is the canonical project reference for the current repository state. If another doc and this file disagree, trust this file first and then verify against the source tree.

Author Of Record: Muhammad Waseem Akram

## 1. Project Snapshot

Lattice Brain is a local, CPU-first AI stack with three main layers:

- Python runtime in `brain/` for normalization, emotion, dialogue planning, routing, memory, internet retrieval, experts, and traces
- TypeScript Fastify interface in `interface/src/` for HTTP and WebSocket access
- Optional Python runtime daemon in `scripts/runtime_daemon.py` for hot local reuse of a loaded runtime
- Optional Rust gRPC router daemon in `router-daemon/` for local routing and expert mapping

The repo is aimed at real execution, not demos:

- memory is persisted in SQLite plus an HNSW index
- experts are manifest-driven and grounded
- traces are collected for offline learning
- CLI chat prints real runtime metrics
- placeholder logic is guarded by tests and scripts

## 2. Current Runtime Shape

The current checked-in runtime includes:

- `language-en`: grounded language and synthesis expert
- `code-general`: repo-grounded code expert
- `geography`: offline geography dataset expert
- `experts/router.json`: trained router artifact
- optional `experts/response-policy.json`: learned response-selection artifact when enough real traces exist

The main product surfaces are:

- CLI chat through `scripts/chat_cli.py`
- Python runtime daemon lifecycle through `scripts/manage_runtime_daemon.py`
- HTTP and WebSocket server through `interface/src/server.ts`
- Python bridge through `scripts/coordinator_bridge.py`
- router daemon lifecycle through `scripts/manage_router_daemon.py`

## 3. Verified Commands

Install dependencies:

```powershell
python -m pip install -r requirements-runtime.txt -r requirements-dev.txt
python -m pip install -r requirements-training.txt
pnpm install
```

Prepare the local runtime:

```powershell
run.bat prepare
```

Open the real CLI chat:

```powershell
run.bat chat
```

Run the Fastify dev server:

```powershell
run.bat dev
```

Other important commands:

```powershell
run.bat bench
run.bat knowledge
run.bat assets
run.bat build
run.bat test
run.bat doctor
run.bat runtime-start
run.bat runtime-status
run.bat runtime-stop
run.bat router-start
run.bat router-status
run.bat router-stop
run.bat skills
```

Useful direct script commands:

```powershell
python scripts/chat_cli.py --once "what is the capital of France"
python scripts/chat_cli.py --once --modality url "https://example.com"
python scripts/prepare_runtime.py --skip-smoke-query
python scripts/build_knowledge_store.py --refresh
python scripts/download_models.py --refresh-knowledge
python scripts/manage_router_daemon.py start --skip-build
python scripts/manage_runtime_daemon.py start
python scripts/manage_runtime_daemon.py status
python scripts/benchmark.py "hello world" --iterations 5
```

## 4. End-To-End Request Flow

The live request path is:

1. A user enters text, a URL, a file upload, voice input, or a CLI prompt.
2. The request hits either the Fastify server or the CLI wrapper.
3. The TypeScript layer forwards structured requests to `scripts/coordinator_bridge.py`.
4. The CLI can either call a local runtime directly or send the request to the hot Python runtime daemon.
5. The bridge calls `brain.runtime.LatticeBrainRuntime.query(...)`.
6. The coordinator normalizes input using an authoritative `modality_hint` when provided.
7. Emotion context is computed from text or voice signals.
8. The router decides expert targets, memory-first behavior, and internet need.
9. Memory recall runs through:
   - SQLite FTS text search
   - HNSW vector search
   - graph neighbor expansion
   - relevance gating before reused memory is trusted
10. Optional live retrieval runs through DuckDuckGo plus fetched page extraction.
11. Experts run through the pool and return grounded outputs.
12. The assembler merges expert or memory outputs into the final answer.
13. The runtime stores grounded results back into memory when appropriate.
14. Feedback traces are recorded for later learning and optional response-policy training.

## 5. Core Python Runtime

Top-level Python runtime files:

- `brain/config.py`: environment-driven runtime settings
- `brain/types.py`: shared contracts
- `brain/dialogue.py`: dialogue-state inference and response planning
- `brain/coordinator.py`: main orchestration path
- `brain/runtime.py`: service wrapper used by CLI and bridge
- `brain/session.py`: session helpers
- `brain/code_symbols.py`: workspace/code symbol utilities

Subpackages:

- `brain/normalizer/`
  - `text_adapter.py`
  - `url_adapter.py`
  - `document_adapter.py`
  - `voice_adapter.py`
  - `__init__.py` with routing logic
- `brain/emotion/`
  - `text_encoder.py`
  - `voice_encoder.py`
  - `fusion.py`
- `brain/memory/`
  - `embedder.py`
  - `sqlite_store.py`
  - `vector_store.py`
  - `graph.py`
- `brain/router/`
  - `model.py`
  - `client.py`
  - `trainer.py`
  - `exporter.py`
  - `labeler.py`
  - `generated/` gRPC bindings
- `brain/experts/`
  - `registry.py`
  - `pool.py`
  - `expert.py`
  - `assembler.py`
  - `types.py`
- `brain/internet/`
  - `search.py`
  - `fetcher.py`
  - `module.py`
  - `types.py`
- `brain/learning/`
  - `feedback.py`
  - `features.py`
  - `policy.py`
  - `scorer.py`
  - `corrector.py`
  - `loop.py`
  - `types.py`

## 6. Interface Layer

The TypeScript interface lives in `interface/src/`:

- `server.ts`: Fastify bootstrap and route registration
- `python_gateway.ts`: long-lived Python bridge process manager
- `types.ts`: request and response schemas
- `routes/query.ts`: text, url, file, and voice routes
- `routes/health.ts`: health endpoint
- `routes/memory.ts`: recall endpoint
- `routes/experts.ts`: expert status endpoint
- `ws/handler.ts` and `ws/stream.ts`: WebSocket query streaming
- `voice/recorder.ts` and `voice/player.ts`: local voice helpers
- `grpc/client.ts`: local gRPC client helpers

HTTP routes currently exposed:

- `POST /query`
- `POST /query/text`
- `POST /query/url`
- `POST /query/file`
- `POST /query/voice`
- `GET /health`
- `GET /memory/recall`
- `GET /experts`

`GET /health` now returns both the old core readiness counters and richer project metadata:

- `project_name`
- `condition`
- `condition_summary`
- `experts_available`
- `expert_ids`
- nested `learning`
- nested `knowledge`
- nested `router`
- nested `storage`

## 7. Rust Router Daemon

The Rust daemon lives in `router-daemon/`:

- `build.rs`: proto build step
- `proto/router.proto`: gRPC schema
- `src/main.rs`: daemon bootstrap
- `src/router.rs`: router artifact loading and inference
- `src/expert_loader.rs`: expert mapping cache
- `src/metrics.rs`: daemon metrics
- `src/session.rs`: session helpers

The daemon is optional at runtime:

- `ROUTER_BACKEND=local` uses artifact routing only
- `ROUTER_BACKEND=grpc` uses the daemon directly
- `ROUTER_BACKEND=auto` uses the hybrid client with artifact fallback

## 8. Experts And Runtime Artifacts

The repo-managed runtime assets are in `experts/`:

- `experts/registry.json`: manifest registry for available experts
- `experts/router.json`: current router artifact
- `experts/base/language-en/manifest.json`
- `experts/base/code-general/manifest.json`
- `experts/base/geography/manifest.json`
- `experts/base/geography/countries.json`
- `experts/lora/`: learning outputs, traces, and optional policy artifacts

These are not demo ONNX blobs. The checked-in experts are manifest- or dataset-driven.

## 9. Scripts And Their Roles

Runtime and operator entrypoints:

- `scripts/chat_cli.py`: interactive and one-shot CLI chat
- `scripts/prepare_runtime.py`: artifact validation, model warmup, daemon start, smoke query
- `scripts/manage_router_daemon.py`: start, stop, and status for the detached router daemon
- `scripts/benchmark.py`: coordinator latency benchmark
- `scripts/coordinator_bridge.py`: JSON-line bridge between Node and Python
- `scripts/diagnose_backends.py`: dependency and backend probe
- `scripts/inspect_memory.py`: memory inspection helper
- `scripts/init_db.py`: local data/bootstrap helper

Training and artifact work:

- `scripts/train_router.py`
- `scripts/train_response_policy.py`
- `scripts/label_data.py`
- `scripts/create_expert.py`
- `scripts/export_expert.py`
- `scripts/download_models.py`
- `scripts/build_knowledge_store.py`
- `scripts/generate_router_stubs.py`

Quality and skill tooling:

- `scripts/guard_no_placeholders.py`
- `scripts/sync_codex_skills.py`
- `scripts/validate_codex_skills.py`
- `scripts/test_rust.ps1`

## 10. CLI Behavior

`scripts/chat_cli.py` supports:

- interactive mode when no prompt is supplied
- one-shot mode with `--once`
- `--modality text|url|file|voice`
- `--health`
- `--experts`
- `--session-id`
- `--skip-warmup`
- `--include-voice-warmup`
- `--no-metrics`
- `--json-metrics`
- `--verbose-warmup`

Interactive commands:

- `/health`
- `/experts`
- `/recall <text>`
- `/quit`
- `/help`

Per-turn metrics include:

- `elapsed_ms`
- `response_tokens`
- `expert_id`
- `response_mode`
- `render_strategy`
- `citations_count`
- `confidence`
- `outcome`
- `query_coverage`
- `entity_match_score`
- `symbol_anchor_score`
- `memory_node_count`
- `experts_loaded`
- `router_backend`
- `vector_backend`
- `decision_trace`

## 11. Preparation Script Behavior

`scripts/prepare_runtime.py` does five main things:

1. verifies or trains `experts/router.json`
2. refreshes generated knowledge packs unless disabled
3. optionally trains `experts/response-policy.json` if enough real traces exist
4. warms text backends, and optionally voice backends
5. optionally starts the router daemon and runs a smoke query

Important runtime honesty rules already built into the script:

- response-policy training is skipped when there is not enough real trace data
- voice warmup is skipped when the home drive has less than 2 GiB free for model cache
- router daemon start reports degraded status instead of pretending success

## 12. Persistent Data And Generated Output

Main generated or machine-local directories:

- `data/`: SQLite DB, HNSW index, cacheable runtime data
- `tmp/`: router daemon state, generated skills, transient outputs
- `dist/`: TypeScript build output
- `target/`: Rust build output
- `node_modules/`: Node dependencies
- `experts/bootstrap/generated/`: generated online and repo-guide knowledge packs

Important runtime files:

- `data/sqlite/metadata.db`
- `data/chroma/memory.index`
- `tmp/router-daemon/state.json`
- `tmp/router-daemon/router-daemon.log`

## 13. Dependency And Toolchain Summary

Python:

- runtime requirements in `requirements-runtime.txt`
- training extras in `requirements-training.txt`
- dev/test tooling in `requirements-dev.txt`
- `pyproject.toml` targets Python `>=3.11,<3.12`

Node:

- `package.json` requires Node `>=20`
- TypeScript is compiled with strict mode through `tsconfig.json`

Rust:

- `rust-toolchain.toml` pins toolchain `1.94.1`
- workspace root is `Cargo.toml`

## 14. Configuration Surface

Active settings are defined in `brain/config.py`, not every historical env var in older docs.

Main settings groups:

- router: `ROUTER_BACKEND`, `ROUTER_MODEL_PATH`, `ROUTER_CONFIDENCE_THRESHOLD`, `GRPC_HOST`, `GRPC_PORT`, `GRPC_TIMEOUT_SEC`
- experts: `EXPERT_DIR`, `LORA_DIR`, `EXPERT_MAX_LOADED`, `EXPERT_IDLE_TIMEOUT_SEC`
- memory: `CHROMA_DIR`, `SQLITE_DIR`, `VECTOR_INDEX_PATH`, `EMBEDDING_BACKEND`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_DIMENSIONS`, `MEMORY_VECTOR_BACKEND`, `MEMORY_RECALL_LIMIT`, `MEMORY_DECAY_DAYS`
- internet: `INTERNET_ENABLED`, `INTERNET_MAX_REQUESTS_PER_QUERY`, `INTERNET_CACHE_TTL_SECONDS`, `INTERNET_ALLOWED_DOMAINS`, `HTTP_TIMEOUT_SEC`, `HTTP_USER_AGENT`, `HTTP_ALLOW_INSECURE_TLS`
- voice: `WHISPER_MODEL`, `VOICE_SAMPLE_RATE`
- learning: `LEARNING_ENABLED`, `LEARNING_BACKEND`, `LEARNING_MIN_SIGNAL_STRENGTH`, `LEARNING_CORRECTION_BATCH_SIZE`
- interface: `API_PORT`, `LOG_LEVEL`
- runtime safety: `MAX_CITATIONS`, `STRICT_RUNTIME`

## 15. Tests And Validation

Python tests live in `tests/python/` and cover:

- types
- normalizer
- emotion
- memory
- experts
- internet
- learning
- coordinator
- runtime integrations
- runtime service
- router gRPC
- quality gates
- skill sync

TypeScript tests live in `tests/typescript/` and cover:

- server routes
- WebSocket flow
- Python gateway behavior

Rust validation runs through:

- `powershell -ExecutionPolicy Bypass -File scripts/test_rust.ps1`

Core validation commands:

```powershell
python -m ruff check brain tests/python scripts
python -m mypy brain
python -m pytest tests/python -q
pnpm test
pnpm run build
python scripts/guard_no_placeholders.py
```

## 16. Current Gaps And Honest Limits

The repo is usable, but these items are still important:

- `experts/response-policy.json` is not guaranteed to exist until enough real traces are collected.
- Voice warmup is real and can be blocked by low disk space on the model-cache drive.
- Cold starts can still be heavy because embedding and text-emotion backends are real model loads.
- Knowledge coverage is much better than before, but math, networking, Linux internals, and more repo-specific operational packs can still be added.
- The repo does not ship a dense local generative model on the critical path, so open-ended creativity is intentionally narrower than a frontier LLM.

## 17. Related Docs

- [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md)
- [README.md](README.md)
- [01_PHYSICS_AND_REASONING.md](01_PHYSICS_AND_REASONING.md)
- [02_ARCHITECTURE_OVERVIEW.md](02_ARCHITECTURE_OVERVIEW.md)
- [03_COMPONENTS_DEEP_DIVE.md](03_COMPONENTS_DEEP_DIVE.md)
- [04_DEPENDENCIES_AND_STACK.md](04_DEPENDENCIES_AND_STACK.md)
- [05_PROJECT_STRUCTURE.md](05_PROJECT_STRUCTURE.md)
- [PLAN.md](PLAN.md)
- [ALGORITHMIC_BRAIN_PLAN.md](ALGORITHMIC_BRAIN_PLAN.md)
- [06_MASTER_BUILD_PROMPT.md](06_MASTER_BUILD_PROMPT.md)
