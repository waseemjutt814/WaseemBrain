<!-- architecture-author: Muhammad Waseem Akram -->

# 02 - Architecture Overview

This file describes the current runtime topology as it exists in the repo today.

## High-Level Shape

```text
CLI / HTTP / WebSocket
        |
        v
TypeScript Fastify Interface or Direct CLI
        |
        v
Python Gateway / Coordinator Bridge
        |
        v
WaseemBrainRuntime
        |
        v
Coordinator
  |      |        |         |
  |      |        |         |
  v      v        v         v
Normalizer Emotion Router  Dialogue Planner
                  |
                  v
          Memory / Internet / Experts
                  |
                  v
            Response Assembler
                  |
                  v
         Streaming Output + Turn Traces
```

## Main Layers

### Interface Layer

The repo exposes two entry surfaces:

- Fastify server in `interface/src/server.ts`
- terminal chat in `scripts/chat_cli.py`

Both eventually call the same Python runtime.

### Bridge Layer

The TypeScript server does not reimplement runtime logic. It delegates to:

- `interface/src/python_gateway.ts`
- `scripts/coordinator_bridge.py`

That bridge keeps transport and orchestration separated.

### Runtime Layer

`brain/runtime.py` owns runtime assembly:

- settings
- memory graph
- expert registry and pool
- router client
- internet module
- coordinator

### Decision Layer

`brain/coordinator.py` drives a request through:

1. normalization
2. emotion encoding
3. routing
4. memory recall
5. optional internet retrieval
6. expert inference
7. response assembly
8. trace recording

### Persistence Layer

State is stored locally through:

- SQLite metadata in `data/sqlite/`
- HNSW vector index in `data/chroma/`
- expert artifacts in `experts/`
- temporary daemon state in `tmp/`

## Routing Modes

The router can operate in three modes:

- local artifact only
- gRPC daemon only
- hybrid auto mode with artifact fallback

That choice is controlled from `brain/config.py`.

## Memory Path

The current memory path is not just a vector lookup. It combines:

- FTS text search
- vector search
- neighbor expansion
- confidence, recency, and session-aware scoring
- relevance gating before a recalled memory is allowed to answer directly

## Expert Path

Experts are loaded from `experts/registry.json` and executed through `brain/experts/pool.py`. The current checked-in experts are:

- `language-en`
- `code-general`
- `geography`

The assembler merges expert outputs into a final response plan rather than blindly concatenating them.

## Learning Path

Learning is offline-oriented:

- turn traces are collected by the feedback system
- scoring features live in `brain/learning/features.py`
- response-policy training lives in `brain/learning/policy.py`
- correction-job logic lives in `brain/learning/corrector.py`

Live inference stays bounded and inspectable.
