# Reasoning Modules

## Purpose
Maintain the bounded reasoning layer that turns memory and workspace evidence into useful coding and chat behavior without a dense local LLM.

## Focus Files
- `brain/experts/registry.py`
- `brain/experts/expert.py`
- `brain/experts/pool.py`
- `brain/experts/assembler.py`
- `brain/coordinator.py`
- `scripts/create_expert.py`

## Rules
- Each module must do one measurable job: answer planning, code retrieval, patch planning, contradiction checks, or grounded synthesis.
- Code reasoning must cite workspace snippets, symbols, or memory hits instead of pretending to infer unseen code.
- Unsupported tasks return explicit limitations; never hide gaps behind generic filler.
- Keep module boundaries sharp so slow logic can be profiled, simplified, or removed.

## Checks
- `python -m pytest tests/python/test_components.py -q`
- `python -m pytest tests/python/test_runtime_integrations.py -q`
- `python scripts/guard_no_placeholders.py`
