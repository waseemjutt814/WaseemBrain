# Component 01 Skill: Shared Types

## Purpose
Build the shared type system in `brain/types.py` so all later components import consistent IDs, domain types, constants, and `Result`.

## Boundaries
- Implement only Component 1 artifacts.
- Do not implement normalizer, emotion, memory, experts, internet, learning, coordinator, TS API, or Rust daemon here.

## Global Context (paste before execution)
- Architecture: Lattice Brain with lightweight router + dynamically loaded experts.
- Stack: Rust router daemon, Python core, TypeScript interface, SQLite metadata.
- Quality rules:
  - Full type annotations only.
  - `Result[T, E]` pattern for fallible operations.
  - Branded types for IDs and domain primitives.
  - No magic numbers; named constants only.
  - Pure-function style where possible.
  - One function, one job.
  - Production-ready output; no TODO placeholders.

## Required Files
- Create/update `brain/types.py`.
- Create/update `tests/python/test_types.py`.

## Implementation Checklist
1. Add a branded type factory:
   - Generic `Branded` helper for nominal typing from primitive values.
   - Define branded aliases: `SessionId`, `ExpertId`, `MemoryNodeId`, `EmbeddingVector`.
2. Add generic `Result[T, E]` as a TypedDict union:
   - Success variant with `ok: True` and success payload.
   - Error variant with `ok: False` and error payload.
   - Constructors: `ok()` and `err()`.
   - Type guards: `is_ok()` and `is_err()`.
3. Add TypedDict domain models:
   - `NormalizedSignal`: `text`, `modality`, optional `raw_audio`, `metadata`, `session_id`.
   - `EmotionContext`: `primary_emotion`, `valence`, `arousal`, `confidence`, `source`.
   - `RouterDecision`: `experts_needed`, `check_memory_first`, `internet_needed`, `confidence`, `reasoning_trace`.
   - `MemoryNode`: `id`, `content`, `embedding`, `tags`, `source`, `created_at`, `last_accessed`, `access_count`, `confidence`.
   - `ExpertOutput`: `expert_id`, `content`, `confidence`, `sources`, `latency_ms`.
4. Add constants object:
   - `SYSTEM` with `MIN_QUERY_LENGTH`, `MAX_EXPERTS_ACTIVE`, `IDLE_TIMEOUT_SEC`, `EMBEDDING_DIMENSIONS`, `MEMORY_RECALL_LIMIT`.
5. Ensure everything is importable from `brain.types`.

## Test Checklist
- `test_types.py` must verify:
  - Branded types reject wrong primitive types at runtime (using `isinstance` checks around constructors/helpers).
  - `ok()` and `err()` shape/values are correct.
  - `is_ok()` / `is_err()` narrow correctly in typed branches.

## Pass Criteria
- `brain/types.py` exports all required symbols.
- Tests for branded values and result guards pass reliably.
- No untyped parameters or placeholder logic.

## Premium Quality Gates (CLI)
- Run formatting/lint/type checks before tests:
  - `python -m ruff check brain tests`
  - `python -m mypy brain`
- Run focused tests:
  - `python -m pytest tests/python/test_types.py -q`
- Merge gate for this component:
  - No ruff errors.
  - No mypy errors in `brain/`.
  - All `test_types.py` cases green.
