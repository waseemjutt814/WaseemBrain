# Build Guide

## Supported Toolchain
- Node.js 20+
- Python 3.11
- Rust only when you want the optional router accelerator

## Recommended Setup
```bash
pnpm install
pnpm run setup:python
pnpm run sync:metadata
pnpm run build
```

`pnpm run setup:python` installs the maintained Python extras from `pyproject.toml`.
`pnpm run sync:metadata` mirrors those Python dependency groups and project metadata back into `package.json`.

## Manual Python Install
With Python 3.11 on your PATH:

```bash
python -m pip install -e '.[runtime,dev]'
```

On Windows machines where `python` is not on PATH, use:

```bash
py -3.11 -m pip install -e ".[runtime,dev]"
```

Training-only extras remain optional:

```bash
python -m pip install -e '.[runtime,dev,training]'
```

## Build Commands
```bash
pnpm run build
pnpm run build:ts
pnpm run build:all
pnpm run build:rust
```

- `build` creates a clean app-only `dist/` and copies `interface/public` into it.
- `build:all` currently resolves to the maintained dist build path.
- `build:python` writes the Python wheel to `dist/python`.
- `build:rust` builds the optional Rust router daemon.

## Runtime Commands
```bash
pnpm run dev
pnpm run dev:interface
pnpm run dev:terminal
pnpm run dev:both
pnpm run dev:backend
pnpm start
pnpm run start:python
```

- `dev` opens the interactive launcher for interface, terminal, interface plus terminal, or backend only.
- `dev:interface` starts the browser surface and auto-starts the backend daemon.
- `dev:terminal` starts the terminal chat and auto-starts the backend daemon.
- `dev:both` keeps the browser surface live while terminal chat runs against the same hot backend.
- `dev:backend` starts only the backend daemon so the interface or terminal can attach later.
- `start` runs the compiled TypeScript server.
- `start:python` runs the Python runtime directly.

## Reporting And Verification
```bash
pnpm run report:inventory
pnpm run report:project
pnpm run verify:project
pnpm run docker:smoke
```

- `report:inventory` writes a repo inventory only.
- `report:project` also runs build, lint, TypeScript tests, Python tests, assistant-surface readiness checks, an optional Docker smoke probe, and a runtime-health snapshot.
- `verify:project` syncs metadata first, then generates the full report.

Generated artifacts:
- `logs/project_report.json`
- `logs/project_report.md`

## Environment Notes
The main runtime knobs live in `.env.example` and `brain/config.py`.

Commonly adjusted variables:
- `ROUTER_BACKEND`
- `INTERNET_ENABLED`
- `INTERNET_ALLOWED_DOMAINS`
- `EXPERT_MAX_LOADED`
- `MEMORY_VECTOR_BACKEND`
- `STRICT_RUNTIME`

## Optional Rust Accelerator
The Rust daemon is not required for the default contract.

Use it when you explicitly want gRPC router acceleration:

```bash
pnpm run build:rust
pnpm run test:rust
```

The living industrial roadmap and completion log are maintained in docs/INDUSTRIAL_REBUILD_PLAN.md.
