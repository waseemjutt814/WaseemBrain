# Waseem Brain Project Report

Generated: 2026-04-08T19:52:10.256419+00:00

## Summary
- Overall status: `pass`
- Files counted: `471`
- Python test files: `25`
- TypeScript test files: `6`
- Python functions: `2120`
- Python async functions: `122`
- Python classes: `538`
- Primary assistant contract: `/ws/assistant`
- Docker smoke: `skipped`

## Environment
- python: `Python 3.11.0`
- node: `v24.14.1`
- npm: `11.11.0`

## Verification Commands
| Command | Status | Passed | Failed | Warnings | Duration (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| `build` | `pass` | 0 | 0 | 0 | 41.572 |
| `lint` | `pass` | 0 | 0 | 0 | 18.258 |
| `guard:placeholders` | `pass` | 0 | 0 | 0 | 1.249 |
| `test:ts` | `pass` | 25 | 0 | 0 | 64.672 |
| `test:python` | `pass` | 146 | 0 | 1 | 23.515 |

## Assistant Surfaces
- Web console: `ready` (interface/public/chat.html)
- Browser shell: `ready` (interface/src/web/app.ts)
- Assistant websocket bridge: `ready` (interface/src/ws/assistant.ts)
- Terminal console: `ready` via `pnpm run chat`
- Runtime daemon: `running` on `127.0.0.1:55881`

## Docker Smoke
- Status: `skipped`
- Reason: docker CLI is not available on PATH

## File Inventory By Top-Level Directory
| Directory | Files |
| --- | ---: |
| `(root)` | 22 |
| `.github` | 1 |
| `.vscode` | 1 |
| `agents_and_runners` | 24 |
| `assets` | 3 |
| `brain` | 78 |
| `build` | 88 |
| `data` | 13 |
| `docker` | 2 |
| `docs` | 44 |
| `experts` | 55 |
| `interface` | 26 |
| `logs` | 11 |
| `router-daemon` | 10 |
| `router_daemon` | 2 |
| `scripts` | 42 |
| `skills` | 13 |
| `tests` | 36 |

## File Inventory By Extension
| Extension | Files |
| --- | ---: |
| `.py` | 257 |
| `.md` | 60 |
| `.json` | 36 |
| `.jsonl` | 35 |
| `.ts` | 26 |
| `.bat` | 7 |
| `.rs` | 6 |
| `.mjs` | 5 |
| `.toml` | 5 |
| `.js` | 4 |
| `.txt` | 4 |
| `<no-extension>` | 4 |
| `.svg` | 3 |
| `.ps1` | 2 |
| `.yaml` | 2 |
| `.yml` | 2 |
| `.1-high` | 1 |
| `.css` | 1 |
| `.db` | 1 |
| `.example` | 1 |
| `.graphml` | 1 |
| `.html` | 1 |
| `.index` | 1 |
| `.lock` | 1 |
| `.node` | 1 |

## Runtime Health Snapshot
```json
{
  "status": "ok",
  "condition": "strong",
  "ready": true,
  "router_backend": "local",
  "vector_backend": "hnsw",
  "experts_available": 8,
  "components": {
    "router_artifact": "ready",
    "response_policy": "ready",
    "expert_registry": "ready",
    "router_daemon": "not-needed",
    "internet": "enabled",
    "knowledge": "ready"
  },
  "capabilities": {
    "model_free_core": true,
    "api_key_required": false,
    "self_improvement_scope": "knowledge-only",
    "router_acceleration_optional": true,
    "default_router_backend": "local"
  }
}
```

## Generated Artifacts
- JSON report: `logs\project_report.json`
- Markdown report: `logs\project_report.md`
