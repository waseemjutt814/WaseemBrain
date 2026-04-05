# Decision Engine

## Purpose
Keep the fast intent and policy engine aligned around compact artifacts that decide which memory, reasoning, and synthesis paths to run.

## Focus Files
- `brain/router/model.py`
- `brain/router/trainer.py`
- `brain/router/exporter.py`
- `brain/router/client.py`
- `router-daemon/src/router.rs`
- `router-daemon/src/main.rs`
- `tests/python/test_router_grpc.py`

## Rules
- The decision engine chooses actions and priorities; it is not a hidden generative model.
- Scoring should be transparent enough to debug with features, labels, and confidence outputs.
- Python and Rust paths must agree on tokenization, hashing, and artifact semantics whenever both remain in use.
- If the daemon stops paying for itself, simplify or remove it instead of preserving ceremony.

## Checks
- `python -m pytest tests/python/test_router_grpc.py -q`
- `powershell -ExecutionPolicy Bypass -File scripts/test_rust.ps1`
