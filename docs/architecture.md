# Architecture Overview

## Runtime Contract
WaseemBrain is an offline-first, model-free brain and agent core. The default path does not require an API key and does not depend on a hidden local LLM fallback.

## Primary Flow
1. `interface/` accepts HTTP and WebSocket requests.
2. `scripts/coordinator_bridge.py` forwards requests to the Python runtime.
3. `brain/runtime.py` loads settings, memory, experts, router, and learning services.
4. `brain/coordinator.py` normalizes input, plans dialogue, routes to experts, and assembles responses.
5. `brain/memory/` provides SQLite metadata plus an HNSW-compatible vector index.
6. `brain/learning/` stores traces and refreshes offline response policy artifacts.

## Routing Modes
- Default: local artifact router
- Optional: gRPC router daemon acceleration
- Policy: the Rust router is an accelerator, not a boot requirement

## Expert Layers
- Grounded experts: language, code, geography
- Offline knowledge experts: cybersecurity, cryptography, algorithms, engineering, advanced security
- System operations expert: explicit tool-oriented system helper

## Memory and Learning
- Metadata is stored in SQLite.
- Vector recall uses native `hnswlib` when available or a portable HNSW-compatible implementation otherwise.
- Learning is knowledge-only: traces, response policy refresh, decay/maintenance, and auditable evolution snapshots.
- Learning does not autonomously edit repo code.
