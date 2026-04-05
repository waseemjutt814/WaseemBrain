# Lattice Brain Skills Source

This directory contains the project-authored source markdown used by `scripts/sync_codex_skills.py` to generate skill folders under `tmp/skills/`.

## What Lives Here

Current source skill files include:

- `component-01-shared-types.md`
- `component-02-input-normalizer.md`
- `component-03-dialogue-state.md`
- `component-03-emotion-encoder.md`
- `component-04-memory-graph.md`
- `component-05-micro-expert-pool.md`
- `component-05-reasoning-modules.md`
- `component-06-internet-module.md`
- `component-06-learning-pipeline.md`
- `component-07-decision-engine.md`
- `component-08-interface-bridge.md`
- `component-09-quality-gates.md`

## Workflow

Generate skills:

```powershell
python scripts/sync_codex_skills.py --output-root tmp/skills
```

Validate generated skills:

```powershell
python scripts/validate_codex_skills.py tmp/skills
```

## Maintenance Rule

If root project docs or component responsibilities change, update the source skill markdown here as needed and regenerate `tmp/skills/`. `tmp/skills/` is generated output, not the source of truth.
