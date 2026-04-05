<!-- components-author: Muhammad Waseem Akram -->

# 03 - Components Deep Dive

This file is a practical module-by-module explanation of the current implementation.

## Shared Contracts

`brain/types.py` defines the shared runtime contracts used across the repo. These types are the glue between normalization, routing, memory, experts, learning, and the public interfaces.

## Input Normalization

The normalization layer lives in `brain/normalizer/` and currently supports:

- raw text
- URLs
- document bytes with filename hints
- voice bytes

Important current behavior:

- explicit `modality_hint` wins
- byte inputs with a non-empty filename hint use `DocumentAdapter`
- plain byte inputs without a file hint fall back to voice normalization

## Emotion Encoding

The emotion layer lives in `brain/emotion/`:

- `text_encoder.py`
- `voice_encoder.py`
- `fusion.py`

This layer provides context for dialogue planning and response style selection. It is not just cosmetic tone shaping.

## Dialogue Planning

`brain/dialogue.py` infers a bounded dialogue state:

- intent
- response style
- clarification need
- workspace relevance
- memory relevance
- confidence

It then builds a response plan such as:

- direct answer
- memory recall answer
- plan
- clarification request

## Coordinator

`brain/coordinator.py` is the core control loop. Key implementation details:

- memory recall can short-circuit expert execution
- recalled memory is filtered by relevance before reuse
- clarification responses are generated when the input is too ambiguous
- traces are recorded for every final response mode
- session traces can be flushed through the runtime for CLI reporting

## Memory

The memory subsystem lives in `brain/memory/` and has three important parts:

- `sqlite_store.py`: metadata, sessions, FTS lookup, provenance, edges
- `vector_store.py`: HNSW index management
- `graph.py`: public memory API and scoring

Important current behavior:

- legacy SQLite schemas are migrated in place when possible
- FTS queries are sanitized to avoid malformed `MATCH` crashes
- stale HNSW indexes are rebuilt from SQLite if counts drift
- HNSW capacity auto-grows before insert exhaustion

## Routing

The routing subsystem lives in `brain/router/`:

- `model.py`: artifact loading and scoring
- `client.py`: artifact, gRPC, and hybrid clients
- `trainer.py`: router training
- `labeler.py`: training-label support
- `exporter.py`: artifact export

The current checked-in artifact is `experts/router.json`.

## Experts

The expert system lives in `brain/experts/`:

- `registry.py` loads manifests
- `pool.py` manages loading and execution
- `expert.py` defines typed expert execution
- `assembler.py` turns multiple outputs into one grounded answer

The current checked-in experts are not generic ONNX chat models. They are specific, typed executors tied to manifests and datasets.

## Internet Retrieval

The internet layer lives in `brain/internet/` and is optional. It combines:

- DuckDuckGo search
- page fetching and extraction
- optional memory-first reuse
- citation capture for grounded answers

It is used only when the router says live retrieval is needed.

## Learning

The learning layer in `brain/learning/` currently supports:

- turn trace capture
- quality features such as entity match and query coverage
- response-policy artifact training
- correction-job scaffolding

This is an offline optimization path, not an excuse to claim fake self-training.

## Interface And Transport

The interface stack includes:

- Fastify routes in `interface/src/routes/`
- WebSocket streaming in `interface/src/ws/`
- Python process bridging in `interface/src/python_gateway.ts`
- JSON-line bridge protocol in `scripts/coordinator_bridge.py`

This keeps transport-specific code out of the core runtime.
