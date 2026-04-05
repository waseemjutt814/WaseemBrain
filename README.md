<!-- internal-author: Muhammad Waseem Akram -->

# Lattice Brain

Lattice Brain is a CPU-first local AI stack built around a Python runtime, a TypeScript Fastify interface, and an optional Rust router daemon. The current repo is designed for real execution: grounded experts, persistent memory, routeable input modalities, measurable traces, and quality gates that reject placeholder behavior.

Author: Muhammad Waseem Akram

## What The Repo Does Today

- Runs local chat and query flows through `brain/` with normalization, emotion tagging, routing, memory recall, expert execution, and response assembly.
- Exposes HTTP and WebSocket entrypoints from `interface/src/`.
- Supports a real terminal chat flow through `scripts/chat_cli.py`.
- Stores memory in SQLite metadata plus an HNSW vector index under `data/`.
- Uses manifest-driven experts in `experts/base/` and a trained router artifact in `experts/router.json`.
- Records turn traces that can later train a response policy when enough real data exists.

## Quick Start

Install Python, Node, and repo dependencies:

```powershell
python -m pip install -r requirements-runtime.txt -r requirements-dev.txt
python -m pip install -r requirements-training.txt
pnpm install
```

Prepare the runtime, warm real backends, and run a smoke query:

```powershell
run.bat prepare
```

Open the interactive CLI chat:

```powershell
run.bat chat
```

Show the branded runtime dashboard only:

```powershell
python scripts/chat_cli.py --dashboard
```

Start the Fastify development server:

```powershell
run.bat dev
```

## Common Commands

```powershell
run.bat prepare
run.bat chat
run.bat bench
run.bat build
run.bat test
run.bat doctor
run.bat router-status
run.bat router-stop
```

Useful direct script entrypoints:

```powershell
python scripts/chat_cli.py --once "what is the capital of France"
python scripts/chat_cli.py --once --modality url "https://example.com"
python scripts/prepare_runtime.py --skip-smoke-query
python scripts/manage_router_daemon.py start --skip-build
python scripts/benchmark.py "hello world" --iterations 5
```

## Interfaces

HTTP routes exposed by the TypeScript layer:

- `POST /query`
- `POST /query/text`
- `POST /query/url`
- `POST /query/file`
- `POST /query/voice`
- `GET /health`
- `GET /memory/recall`
- `GET /experts`

CLI features exposed by `scripts/chat_cli.py`:

- one-shot queries with `--once`
- interactive chat with `/health`, `/experts`, `/recall <text>`, `/quit`
- branded `Waseem Brain` dashboard with `/status`, `/dashboard`, `/learning`, `/project`, and `/clear`
- per-turn metrics such as `response_tokens`, `expert_id`, `response_mode`, `confidence`, and `decision_trace`

## Documentation Map

- [COMPLETE_STRUCTURE_AND_DETAILS.md](COMPLETE_STRUCTURE_AND_DETAILS.md): canonical full-project guide
- [01_PHYSICS_AND_REASONING.md](01_PHYSICS_AND_REASONING.md): design principles and constraints
- [02_ARCHITECTURE_OVERVIEW.md](02_ARCHITECTURE_OVERVIEW.md): runtime topology and data flow
- [03_COMPONENTS_DEEP_DIVE.md](03_COMPONENTS_DEEP_DIVE.md): module-by-module implementation notes
- [04_DEPENDENCIES_AND_STACK.md](04_DEPENDENCIES_AND_STACK.md): dependency groups and toolchain
- [05_PROJECT_STRUCTURE.md](05_PROJECT_STRUCTURE.md): source tree map
- [PLAN.md](PLAN.md): current near-term roadmap and remaining gaps
- [ALGORITHMIC_BRAIN_PLAN.md](ALGORITHMIC_BRAIN_PLAN.md): long-range product direction
- [06_MASTER_BUILD_PROMPT.md](06_MASTER_BUILD_PROMPT.md): contributor prompt for AI-assisted work

## Verification

```powershell
python -m ruff check brain tests/python scripts
python -m mypy brain
python -m pytest tests/python -q
python -m compileall brain tests/python scripts
python scripts/guard_no_placeholders.py
pnpm test
pnpm run build
powershell -ExecutionPolicy Bypass -File scripts/test_rust.ps1
```

## Honest Notes

- `scripts/prepare_runtime.py` only trains `experts/response-policy.json` when real trace files exist. Otherwise it reports an honest skip.
- Voice warmup is real, not mocked, and is skipped when the system drive has less than 2 GiB free for model cache.
- `brain/runtime.py` still reports `ready: true` in health snapshots even when the system is running in a degraded state. That gap is tracked in [PLAN.md](PLAN.md).
- The repo currently ships three checked-in experts: `language-en`, `code-general`, and `geography`.

[INFO] Starting local router daemon...

                    W   W  AAAAA  SSSSS  EEEEE  EEEEE  M   M        BBBB   RRRR    AAAAA  III  N   N
                    W   W  A   A  S      E      E      MM MM        B   B  R   R   A   A   I   NN  N
                    W W W  AAAAA  SSSS   EEE    EEE    M M M        BBBB   RRRR    AAAAA   I   N N N
                    WW WW  A   A      S  E      E      M   M        B   B  R R     A   A   I   N  NN
                    W   W  A   A  SSSSS  EEEEE  EEEEE  M   M        BBBB   R  RR   A   A  III  N   N
                             Waseem Brain Terminal | Runtime | Memory | Experts | Learning
========================================================================================================================
+- Project Condition --------------------------------------------------------------------------------------------------+
| brain name       : Waseem Brain                                                                                      |
| condition        : READY | response policy still in rule-default mode                                                |   
| session          : cli-1774707039                                                                                    |   
| pipeline         : normalize > emotion > route > memory > experts > render                                           |   
+----------------------------------------------------------------------------------------------------------------------+   
+- Runtime Status -----------------------------------------------------------------------------------------------------+   
| router           : auto | artifact ready | daemon pid 13564 port 50051 | uptime 14.1h                                |   
| memory           : 3 nodes | backend hnsw | index data\chroma\memory.index                                           |   
| experts          : 3 available | 0 loaded | max 3                                                                    |   
| expert ids       : language-en, code-general, geography                                                              |   
| internet         : enabled | max 5 requests per query                                                                |   
| warmup           : text=ready | embedder=sentence-transformers | voice=not warmed                                    |   
+----------------------------------------------------------------------------------------------------------------------+   
+- Learning Status ----------------------------------------------------------------------------------------------------+
| learning         : enabled | backend auto                                                                            |   
| response policy  : rule-default                                                                                      |   
| trace corpus     : 0 session files | 0 turns                                                                         |   
| expert traces    : 0 files | 0 turns                                                                                 |   
| training jobs    : 0 pending manifests | 0 datasets                                                                  |   
| learning phase   : collecting real traces                                                                            |   
+----------------------------------------------------------------------------------------------------------------------+   
+- Commands -----------------------------------------------------------------------------------------------------------+
| /status or /dashboard : full branded runtime dashboard                                                               |   
| /learning             : learning-only status panel                                                                   |   
| /project              : project condition summary                                                                    |   
| /health               : raw runtime health snapshot                                                                  |   
| /experts              : currently loaded expert ids                                                                  |   
| /recall <text>        : inspect memory recall results                                                                |   
| /clear                : redraw the Waseem Brain screen                                                               |   
| /quit                 : exit the terminal chat                                                                       |   
+----------------------------------------------------------------------------------------------------------------------+   
Waseem Brain terminal is live. Type /status to see the full dashboard.

waseem@terminal>