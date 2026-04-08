<!-- implementation-log-author: Muhammad Waseem Akram -->

# Implementation Log

This file tracks concrete repository improvements as they land. It is meant to be a living operator and contributor log, not marketing copy.

## 2026-03-29

### Multipart Upload Path Fix

Files:

- `interface/src/server.ts`
- `tests/typescript/server.test.ts`

What changed:

- Moved `@fastify/multipart` registration to the root Fastify app instead of a child plugin scope.
- Moved `@fastify/websocket` registration and WebSocket route wiring to the root app as well.
- Added direct multipart route tests for:
  - `POST /query/file`
  - `POST /query/voice`
- Verified that uploaded payloads are converted into the expected Python bridge request shape with:
  - correct `modality`
  - correct `filename`
  - correct `mime_type`
  - correct `session_id`
  - correct base64-encoded content

Why it matters:

- The upload routes were previously at risk because the multipart decorator lived inside a child plugin while the routes lived on the root app.
- The new arrangement makes file and voice uploads first-class root routes instead of relying on plugin-scope luck.

### Knowledge Store Expansion

Files:

- `scripts/build_knowledge_store.py`
- `experts/knowledge-manifest.json`
- `scripts/download_models.py`
- `brain/bootstrap.py`

What changed:

- Added manifest-driven ingestion for repo-local Markdown files in addition to online URLs.
- Expanded the generated corpus with:
  - official coding docs
  - science and earth docs
  - repo guide packs
- Added generated-pack cleanup during refresh so old datasets do not linger.
- Allowed recursive bootstrap loading so `experts/bootstrap/generated/*.json` becomes part of the same seed path as checked-in packs.

Current corpus after refresh:

- static checked-in cards: `21`
- generated cards: `32`
- total local corpus: `53`
- datasets visible to bootstrap: `5`

Why it matters:

- The runtime now answers a broader class of general, coding, and repo-specific questions from grounded local data.
- The local corpus is no longer limited to hand-authored bootstrap cards.

### Learning And Runtime State

Files:

- `brain/runtime.py`
- `scripts/coordinator_bridge.py`
- `scripts/chat_cli.py`
- `scripts/prepare_runtime.py`

What changed:

- Real session traces are persisted from both CLI and Python bridge flows.
- Response policy refresh happens automatically when enough real traces exist.
- Runtime and prepare status expose richer knowledge and learning state.
- The CLI dashboard now reflects knowledge-pack counts and learning events.

Why it matters:

- The system now gets better from real usage instead of staying static between runs.
- Operators can see whether the brain is empty, partially seeded, or fully warmed.

### Hot Runtime Daemon And Honest Health Signals

Files:

- `scripts/runtime_client.py`
- `scripts/runtime_daemon.py`
- `scripts/manage_runtime_daemon.py`
- `scripts/chat_cli.py`
- `scripts/prepare_runtime.py`
- `run.bat`
- `brain/runtime.py`

What changed:

- Fixed the Python runtime daemon protocol so `health`, `experts`, `recall`, `query`, and `shutdown` all write valid responses back to clients.
- Added a proper hot-runtime client abstraction that lets the CLI and prepare flow talk to either:
  - a live daemon
  - or a local in-process runtime fallback
- Increased runtime-daemon client timeouts so first real queries do not fail just because the runtime takes longer than 30 seconds to produce the first token.
- Made `scripts/manage_runtime_daemon.py` robust against stale state by:
  - detecting an already-listening daemon on the configured port
  - re-adopting that listener into `tmp/runtime-daemon/state.json`
  - waiting for the new daemon to bind and accept connections before reporting startup success
- Added `run.bat` commands for:
  - `runtime-start`
  - `runtime-status`
  - `runtime-stop`
- Made `run.bat chat` automatically start the hot Python runtime daemon before opening the terminal chat.
- Extended `scripts/prepare_runtime.py` so smoke and health checks can run through the daemon and report `runtime_mode`.
- Tightened `brain/runtime.py` router reporting so stale router state is no longer treated as healthy when `127.0.0.1:50051` is unreachable.

Why it matters:

- Repeated CLI sessions can reuse a loaded runtime instead of paying the full local cold-start cost every time.
- Preparation output now tells the truth about whether the system is using a hot daemon or a local fallback.
- Operator health output is more trustworthy when the Rust router daemon state file exists but the actual endpoint is down.

### Validation Run

Commands run:

```powershell
python scripts/build_knowledge_store.py --refresh
python -m pytest tests/python/test_knowledge_builder.py -q
python -m pytest tests/python/test_bootstrap_and_learning.py -q
python -m py_compile brain/runtime.py scripts/chat_cli.py scripts/prepare_runtime.py scripts/runtime_client.py scripts/runtime_daemon.py scripts/manage_runtime_daemon.py
python scripts/manage_runtime_daemon.py start
python scripts/manage_runtime_daemon.py status
python scripts/chat_cli.py --dashboard --runtime-daemon always --skip-warmup --plain-ui
python scripts/chat_cli.py --once "hello" --runtime-daemon always --skip-warmup --plain-ui --no-metrics
python scripts/prepare_runtime.py --skip-knowledge-refresh --skip-router-start --json-only
pnpm test
python scripts/guard_no_placeholders.py
```

Observed state:

- generated knowledge store build succeeded
- multipart upload tests passed
- placeholder guard passed
- fresh temp runtime boot reported:
  - `knowledge_cards=53`
  - `knowledge_datasets=5`
  - `memory_node_count=53`
  - `condition=strong`
- hot runtime daemon validated with:
  - dashboard access through `--runtime-daemon always`
  - one-shot `hello` query over the daemon
  - prepare smoke query over the daemon
- daemon-backed prepare run reported:
  - `runtime_mode=daemon`
  - smoke query answered with grounded Paris memory recall
  - real trace count grew to `10`
  - trained trace count refreshed to `10`

## 2026-03-28

### Earlier Runtime Foundation Work

Highlights from the immediately preceding work:

- branded terminal dashboard and metrics in `scripts/chat_cli.py`
- richer `prepare` summaries in `scripts/prepare_runtime.py`
- built-in bootstrap knowledge packs
- generated knowledge assets commands in `run.bat`
- response-policy auto-refresh from real traces
- router sample dataset and safer router training defaults

This section is intentionally brief because the canonical current-state docs now describe the resulting system in more detail.
