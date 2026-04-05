# Lattice Brain Current Plan

This file tracks the near-term roadmap for the current codebase. It is intentionally practical and should stay tied to real files, real behavior, and real gaps.

## Current Status

The repo already has a usable local runtime:

- CLI chat works through `scripts/chat_cli.py`
- preparation and smoke validation work through `scripts/prepare_runtime.py`
- memory uses SQLite plus HNSW instead of placeholder storage
- routing works from `experts/router.json` with optional daemon fallback
- checked-in bootstrap knowledge fills the runtime with built-in talk and coding cards
- generated knowledge packs can be built from curated online sources in `experts/knowledge-manifest.json`
- generated repo-guide packs now pull local Markdown architecture docs into the same memory seed path
- feedback traces are persisted and can auto-refresh the response policy from real usage
- a hot Python runtime daemon can keep the runtime loaded between CLI and prepare runs
- placeholder guardrails and test suites are in place

## Recently Completed

- memory index resilience:
  - stale HNSW indexes are rebuilt from SQLite when needed
  - HNSW capacity grows before inserts exhaust the index
- text recall safety:
  - SQLite FTS queries are tokenized and sanitized
  - invalid FTS queries fail closed instead of crashing recall
- modality handling:
  - explicit `modality_hint` now wins over content sniffing
  - byte inputs with filename hints route through document normalization
- chat ergonomics:
  - CLI warmup, one-shot mode, session ids, metrics, and health helpers are in place
- memory-answer trust:
  - recalled memory is relevance-gated before it can short-circuit expert inference
- built-in knowledge:
  - runtime bootstraps 21 checked-in knowledge cards from `experts/bootstrap/`
  - short greeting queries now have a grounded welcome path instead of an empty failure
- generated knowledge store:
  - `scripts/build_knowledge_store.py` fetches curated official sources into `experts/bootstrap/generated/`
  - local repo Markdown guides can also be ingested through manifest-driven file sources
  - `scripts/download_models.py` now does real asset warmup plus knowledge-store refresh
- upload-path reliability:
  - `@fastify/multipart` registration now lives on the root app
  - direct TypeScript tests now cover `POST /query/file` and `POST /query/voice`
- self-learning path:
  - session traces are persisted from CLI and Python bridge flows
  - response policy can refresh automatically once at least three real traces exist
- hot runtime service mode:
  - `scripts/runtime_daemon.py` now keeps one runtime alive behind a local TCP protocol
  - `scripts/manage_runtime_daemon.py` can start, stop, status-check, and re-adopt a live daemon if the state file goes stale
  - `run.bat chat` now starts the hot runtime daemon automatically
- health truthfulness:
  - router daemon state now degrades when the configured gRPC endpoint is not reachable
  - `scripts/prepare_runtime.py` reports whether smoke and status ran through the daemon or an in-process fallback

## Highest Priority Remaining Work

1. Expand real knowledge coverage.
   The runtime now has 53 seeded cards across static and generated packs, but the next gains come from adding more grounded cards and datasets for math, systems, networking, and deeper repo-specific operational knowledge.

2. Extend hot-runtime coverage beyond the CLI.
   The Python runtime daemon now helps `chat` and `prepare`, but the HTTP and WebSocket surfaces still instantiate their own runtime path. The biggest UX gain now is to let the interface layer optionally reuse the same hot service.

3. Tighten runtime health and documentation around voice readiness.
   Voice warmup is real and currently depends on at least 2 GiB free on the cache drive. That behavior should stay explicit in operator-facing output.

## Recommended Execution Order

1. health truthfulness
   Completed for the current runtime snapshot shape; keep refining if new degraded states are added.
2. broader response-policy trace corpus and refresh heuristics
3. extend the hot runtime daemon to HTTP and bridge surfaces where it makes sense
4. broader end-to-end CLI and HTTP regression coverage

## Testing Focus

When the next round of work lands, the minimum regression sweep should include:

```powershell
python -m pytest tests/python/test_memory.py -q
python -m pytest tests/python/test_components.py -q
python -m pytest tests/python/test_runtime_integrations.py -q
pnpm test
python scripts/guard_no_placeholders.py
```

## Out Of Scope For This Plan

- adding a dense local LLM to the critical path
- fake training outputs or placeholder experts
- undocumented capability claims that are not backed by the repo
