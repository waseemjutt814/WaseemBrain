# Waseem Brain Industrial Rebuild Plan

## Vision Lock
- Product shape: local-first single-user assistant OS with optional self-hosted Docker deployment.
- Default posture: no local model and no API key required.
- Upgrade path: hybrid provider support stays optional and additive.
- Safety model: read-safe actions may run directly; state-changing actions require preview, explicit confirmation, and audit logging.
- Primary contract: `/ws/assistant` plus `/health`, `/api/catalog`, and `/api/actions`.

## Milestones
- [x] M1: Lock the assistant-first product direction and create the living roadmap/progress file.
- [x] M2: Expand the assistant action surface for workspace, verification, and runtime control.
- [x] M3: Extend project reporting with assistant-surface readiness and Docker smoke status.
- [x] M4: Harden Docker Compose for the industrial single-tenant deployment path.
- [x] M5: Align README and canonical docs with the maintained assistant contract.
- [x] M6: Keep `pnpm test` green and verify `pnpm run verify:project` produces truthful artifacts.

## Working Defaults
- Web and terminal share one assistant event grammar and one approval model.
- Compatibility HTTP and legacy websocket routes remain available, but they are secondary integration paths.
- The runtime defaults to `local` mode; hybrid providers remain optional upgrades when configured.
- The web UI remains English-first; assistant conversation may be multilingual.
- Docker scope in this pass is single-tenant self-hosting only. No SaaS tenancy, auth, or Kubernetes work is included.

## Current State
- Assistant-first browser and terminal surfaces both target `/ws/assistant` as the maintained session contract, and the browser now ships as a fuller Operating Console with a workspace rail, center chat/dashboard views, and inspector dock.
- The local action surface now includes repository summary/search, audit log inspection, verification commands, runtime status, runtime daemon lifecycle control, Docker smoke checks, and protected firewall operations.
- `pnpm run verify:project` now emits `logs/project_report.json` and `logs/project_report.md` with inventory counts, test counts, assistant-surface readiness, runtime health, and Docker smoke evidence.
- Docker Compose is hardened around the `brain-runtime` and `interface` services, internal runtime networking, health-based startup ordering, and persistent `data`, `logs`, and `tmp` mounts.
- Root and canonical docs now reflect the assistant-first contract, local default mode, full verification workflow, Docker smoke command, and this living roadmap.

## Remaining Blockers
- Host-level Docker smoke proof is currently `skipped` on this machine because the Docker CLI is not available on `PATH`.
- When Docker is available, rerun `pnpm run docker:smoke` to replace the skipped result with live boot and persistence evidence.

## Completion Log
### 2026-04-08 - Baseline
- Created the living industrial rebuild roadmap to act as the canonical plan and progress ledger.
- Locked the product defaults around local-first behavior, structured assistant sessions, and approval-first protected actions.

### 2026-04-08 - Implementation Pass
- Completed M2 by expanding the assistant action registry, previews, execution paths, and classifier coverage for repo inspection, verification, audit logs, runtime daemon control, and Docker smoke.
- Completed M3 by extending project reporting to include assistant-surface readiness, runtime daemon visibility, Docker smoke status, and truthful markdown/json artifacts.
- Completed M4 by hardening `docker-compose.yml`, shifting the runtime to the internal network only, keeping the interface publicly exposed, and mounting persistent `data`, `logs`, and `tmp` volumes.
- Completed M5 by aligning `README.md`, `docs/README.md`, `docs/build.md`, `docs/testing.md`, `docs/api.md`, and `docs/components.md` with the maintained assistant contract and deployment workflow.
- Completed M6 by keeping the fast gate green, adding regression coverage for the new assistant/reporting paths, syncing command metadata, and producing fresh verification artifacts.
- Remaining blocker after implementation: Docker smoke is implemented truthfully but the host cannot execute it until the Docker CLI is installed or exposed on `PATH`.

### 2026-04-08 - Interface Rebuild Follow-Up
### 2026-04-08 - Interface Reset Phase
- Removed the previous browser shell direction and rebuilt the interface around a more professional operating-console structure: left navigation rail, center workspace views, right inspector dock, and distinct tabs for chat, Brain Matrix, automations, and memory.
- Reintroduced `interface/public/chat.html` and `interface/public/index.css` as full source-owned UI files instead of leaning on a stale generated shell.
- Reworked the frontend interaction model so actions live in a dedicated automation workspace, memory recall lives in a dedicated memory workspace, and the inspector focuses on overview, API, skills, and settings.
- Locked the new UI direction around current professional AI product patterns: source-aware chat, persistent project context, and clean separation between conversation, evidence, and operational controls.

- Replaced the browser shell with a fuller command-center layout: runtime pulse rail, command board, streaming transcript studio, action palette, memory panel, and settings snapshot.
- Rewrote the browser-side assistant state management so the UI now tracks proof, memory recall, action selection, quick action shortcuts, runtime metadata, and websocket-driven streaming in one maintained flow.
- Replaced the old repetitive local fallback line with route-aware local guidance so coding, repo, web, greeting, and action requests no longer collapse into the same canned answer.
- Added regression checks for the new memory panel label and the query-aware local fallback path.

## Verification History
- 2026-04-08: `pnpm test` -> `pass`; lint passed, placeholder guard passed, TypeScript tests passed `24/24`, and Python tests passed `145/145` with one deprecation warning from `brain/normalizer/voice_adapter.py`.
- 2026-04-08: `pnpm run verify:project` -> `pass`; generated `logs/project_report.json` and `logs/project_report.md`, counted `471` files, recorded `5` verification commands passed and `0` failed, confirmed primary assistant contract `/ws/assistant`, and captured the runtime daemon as running on `127.0.0.1:55881`.
- 2026-04-08: `pnpm run docker:smoke` -> `skipped`; reason: docker CLI is not available on `PATH`.

- 2026-04-08: `pnpm run typecheck:ts` -> `pass`; the rebuilt browser shell, new memory panel contract, and assistant dashboard state model compiled cleanly.
- 2026-04-08: `pnpm exec tsc -p tsconfig.web.json` plus `node scripts/annotate_generated_js.mjs interface/generated` -> `pass`; direct browser asset compilation succeeded after the standard `build:web` wrapper hit a local `EPERM` while removing the existing `interface/generated` directory.
- 2026-04-08: `pnpm run test:ts` -> `pass`; `25/25` TypeScript tests passed after rerunning outside the sandbox because the Node test runner needed unrestricted spawn rights.
- 2026-04-08: `node scripts/run_python.mjs -m pytest tests/python/test_assistant_runtime.py -q` -> `pass`; `4/4` assistant runtime tests passed, including the new query-aware fallback assertion.
- 2026-04-08: `pnpm run build:web` -> `pass`; the new source-owned browser shell built cleanly and regenerated `interface/generated` without the earlier permission failure.
- 2026-04-08: `pnpm run test:ts` -> `pass`; `25/25` TypeScript tests passed after the full interface reset.
- 2026-04-08: `pnpm run guard:placeholders` -> `pass`; the assistant-surface guard was aligned with the new workspace-based interface contract and now validates the rebuilt shell truthfully.
- 2026-04-08: `pnpm run verify:project` -> `pass`; regenerated `logs/project_report.json` and `logs/project_report.md` after the interface reset, with assistant surfaces back to `ready` and `5` verification commands passed.
