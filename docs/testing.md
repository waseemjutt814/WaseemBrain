# Testing Guide

## Main Commands
```bash
pnpm run lint
pnpm run typecheck:ts
pnpm run test:ts
pnpm run test:python
pnpm run test:all
```

## What The Maintained Gate Covers
- `pnpm run lint` runs the maintained-core Python lint and type checks.
- `pnpm run typecheck:ts` checks the interface and TypeScript tests without writing to `dist/`.
- `pnpm run test:ts` typechecks and then runs the TypeScript interface tests.
- `pnpm run test:python` runs the Python runtime and integration suite.
- `pnpm run test:all` runs the TypeScript and Python suites together.

Rust router tests remain optional through `pnpm run test:rust`.

## Coverage
```bash
pnpm run test:coverage
```

## Full Project Report
```bash
pnpm run report:project
```

That command writes:
- `logs/project_report.json`
- `logs/project_report.md`

It also records pass or fail results for build, lint, TypeScript tests, Python tests, assistant-surface readiness, Docker smoke status, and a runtime-health snapshot.

## Direct Python Entry Points
If you want to run pytest without pnpm:

```bash
py -3.11 -m pytest tests/python -q
```

On macOS or Linux, the equivalent command is typically:

```bash
python3.11 -m pytest tests/python -q
```

## Notes
- The default verification target is the maintained runtime surface, not every historical sandbox module in the repo.
- Pytest cache warnings may still appear on this machine because `.pytest_cache` is access-restricted.

pnpm run docker:smoke is the direct industrial deployment check for compose boot, assistant reachability, and restart persistence.
