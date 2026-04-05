# Component 05 Skill: Micro-Expert Pool

## Purpose
Implement expert registry, lazy ONNX loading, mmap-based memory behavior, eviction strategy, concurrent inference, and multi-expert response assembly.

## Dependencies
- `onnxruntime`
- `numpy`
- `asyncio` + `concurrent.futures`
- JSON metadata registry in `experts/registry.json`

## Required Files
- `brain/experts/registry.py`
- `brain/experts/expert.py`
- `brain/experts/pool.py`
- `brain/experts/assembler.py`
- `tests/python/test_experts.py`

## Implementation Checklist
1. `registry.py`:
   - Load/validate `registry.json` from `EXPERT_DIR`.
   - Schema fields: `id`, `name`, `domains`, `file`, `size_mb`, `quantized`, `description`.
   - Methods:
     - `get(expert_id) -> Result[ExpertMeta, str]`
     - `find_by_domain(domain) -> list[ExpertMeta]`
     - `all() -> list[ExpertMeta]`
     - `validate() -> Result[None, str]` ensuring referenced files exist.
2. `expert.py`:
   - Wrap one ONNX model per `Expert`.
   - Lazy session creation on first `infer`.
   - mmap model file via `numpy.memmap`; feed model bytes to `onnxruntime.InferenceSession`.
   - Methods:
     - `infer(text, max_tokens) -> Result[ExpertOutput, str]`
     - `unload() -> None`
     - `is_loaded() -> bool`
     - `last_used_at() -> float`
   - Track latency (`last_latency_ms`) for each inference.
3. `pool.py`:
   - Keep loaded experts dictionary.
   - Use `SYSTEM.MAX_EXPERTS_ACTIVE` and `SYSTEM.IDLE_TIMEOUT_SEC`.
   - `load(expert_id)`:
     - return existing expert if loaded (touch last-used).
     - if full, evict least-recently-used expert.
     - preload pages via light/no-op infer.
   - `infer(expert_ids, text)`:
     - ensure each expert loaded.
     - run concurrently using `asyncio.gather` + `ThreadPoolExecutor`.
   - `evict_idle()`:
     - unload experts idle beyond timeout.
     - return evicted IDs.
   - run idle eviction on 10-second periodic background timer.
4. `assembler.py`:
   - Merge `list[ExpertOutput]` into final response payload.
   - Single output -> direct return.
   - Multi-output agreement -> merge with highest-confidence framing.
   - Conflict -> structured multi-perspective output with confidence and conflict marker.

## Test Checklist
- Registry validation with temporary minimal registry.
- Expert lazy loading (`session is None` before first infer).
- Pool eviction at `MAX_EXPERTS_ACTIVE + 1`.
- Concurrent inference path returns combined outputs.
- Assembler conflict output includes both perspectives.

## Pass Criteria
- Pool respects capacity and idle policy.
- Loading/inference paths always return typed `Result`.
- Conflict handling is explicit and machine-parseable.

## Premium Quality Gates (CLI)
- Static checks:
  - `python -m ruff check brain tests`
  - `python -m mypy brain`
- Targeted tests:
  - `python -m pytest tests/python/test_experts.py -q`
- Concurrency confidence run:
  - run `test_experts.py` multiple times to catch flaky async issues.
- Merge gate:
  - eviction scenario (`MAX_EXPERTS_ACTIVE + 1`) always stable.
  - lazy-load invariant (`session is None` before infer) remains true.
