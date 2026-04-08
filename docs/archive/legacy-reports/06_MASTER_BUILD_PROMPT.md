# 06 - Contributor Prompt

Use this prompt when you want Codex or another coding model to work on the current WaseemBrain repo without drifting into stale architecture assumptions.

## Prompt

```text
You are working inside the current WaseemBrain repository.

Project summary:
- WaseemBrain is a CPU-first local AI stack.
- Python in `brain/` owns normalization, emotion, dialogue planning, routing, memory, experts, internet retrieval, and learning traces.
- TypeScript in `interface/src/` owns Fastify HTTP/WebSocket transport and the Python bridge.
- Rust in `router-daemon/` owns the optional gRPC router daemon.
- The checked-in runtime artifacts are in `experts/`.

Hard rules:
- No fake work, no dummy artifacts, no placeholder logic, no demo experts.
- Do not describe capabilities that are not present in the repo.
- Inspect the current files before changing behavior.
- Keep the runtime grounded in memory, evidence, manifests, datasets, and traces.
- If you add or change architecture, update the markdown docs in the repo root to match.
- Prefer extending the current implementation over inventing a second architecture beside it.

Current entrypoints:
- `run.bat prepare`
- `run.bat chat`
- `run.bat dev`
- `run.bat test`
- `python scripts/chat_cli.py --once "..."`
- `python scripts/prepare_runtime.py`

Current important files:
- `brain/coordinator.py`
- `brain/runtime.py`
- `brain/dialogue.py`
- `brain/memory/sqlite_store.py`
- `brain/memory/vector_store.py`
- `interface/src/server.ts`
- `scripts/chat_cli.py`
- `scripts/prepare_runtime.py`
- `experts/registry.json`
- `experts/router.json`

Validation expectations:
- run focused tests for the area you change
- run broader regressions when touching shared runtime paths
- keep `scripts/guard_no_placeholders.py` passing

Before making assumptions, check:
- `README.md`
- `COMPLETE_STRUCTURE_AND_DETAILS.md`
- `PLAN.md`
- `brain/config.py`

If the repo and docs disagree, trust the source code first and then fix the docs.
```

## Why This File Exists

Older versions of this repo had aspirational build prompts that no longer matched the implementation. This file now acts as a current-state contributor prompt rather than a rebuild-from-scratch spec.
