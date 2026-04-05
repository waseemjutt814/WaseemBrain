# Quality Gates

## Purpose
Keep the repo hard to regress by enforcing dependency splits, placeholder guards, offline-first rules, skill sync, and CI checks.

## Focus Files
- `requirements-runtime.txt`
- `requirements-training.txt`
- `requirements-dev.txt`
- `scripts/guard_no_placeholders.py`
- `scripts/sync_codex_skills.py`
- `scripts/validate_codex_skills.py`
- `.github/workflows/ci.yml`

## Rules
- Runtime installs stay lean; training/export dependencies are separate.
- CI must fail if stub/demo runtime code or checked-in fake artifacts reappear.
- Generated skills must include anti-placeholder, runtime expectation, and brain-plan references.
- Reject hidden dense-local-model or hidden-network shortcuts in critical runtime paths.
- Tests should guard the quality gates themselves, not just the runtime.

## Checks
- `python -m pytest tests/python/test_skill_sync.py -q`
- `python -m pytest tests/python/test_quality_gates.py -q`
- `python scripts/guard_no_placeholders.py`
