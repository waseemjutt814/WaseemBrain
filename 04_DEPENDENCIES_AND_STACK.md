<!-- dependencies-author: Muhammad Waseem Akram -->

# 04 - Dependencies And Stack

This file lists the active stack used by the current repo. It intentionally avoids older architectural claims that no longer match the code.

## Python Runtime Stack

Runtime requirements come from `requirements-runtime.txt`:

- `onnxruntime`: runtime inference support
- `hnswlib`: HNSW vector index for memory recall
- `faster-whisper`: voice transcription path
- `vaderSentiment`: text sentiment features
- `trafilatura`: web content extraction
- `httpx[http2]`: async HTTP fetching
- `pypdf`: PDF extraction
- `python-docx`: DOCX extraction
- `pandas` and `openpyxl`: spreadsheet and tabular document handling
- `pillow`: image support for file preprocessing helpers
- `langdetect`: text language detection
- `duckduckgo-search`: web search
- `feedparser`: feed parsing
- `tenacity`: retry helpers
- `grpcio` and `protobuf`: gRPC support
- `pydantic`: schema and validation helpers
- `python-dotenv`: environment loading helpers
- `loguru`: logging support
- `numpy`: numeric utilities

## Python Training And Export Extras

Training extras come from `requirements-training.txt` and are only needed for training or export jobs:

- `onnx`
- `torch`
- `transformers`
- `peft`
- `datasets`
- `sentence-transformers`
- `optimum[onnxruntime]`
- `scikit-learn`
- `grpcio-tools`

## Python Dev And Test Tooling

Dev tooling comes from `requirements-dev.txt`:

- `pytest`
- `pytest-asyncio`
- `pytest-httpx`
- `respx`
- `mypy`
- `ruff`

## Node And TypeScript Stack

`package.json` defines the interface stack:

- `fastify`
- `@fastify/multipart`
- `@fastify/static`
- `@fastify/websocket`
- `node-record-lpcm16`
- `ws`
- `zod`

Dev tooling:

- `typescript`
- `tsx`
- `@types/node`
- `@types/ws`

The project targets Node `>=20` and compiles with strict TypeScript settings from `tsconfig.json`.

## Rust Stack

The router daemon workspace uses:

- `tokio`
- `tonic`
- `prost`
- `serde`
- `serde_json`
- `memmap2`
- `thiserror`

Build-time dependencies:

- `tonic-build`
- `protoc-bin-vendored`

The workspace toolchain is pinned through `rust-toolchain.toml` to Rust `1.94.1`.

## Tooling Files

- `pyproject.toml`: Python project config, Ruff, mypy, pytest
- `package.json`: Node scripts and dependencies
- `Cargo.toml`: workspace root
- `router-daemon/Cargo.toml`: daemon crate dependencies
- `tsconfig.json`: TypeScript compiler configuration
- `requirements.txt`: convenience include for runtime requirements

## Important Reality Checks

- The live memory path uses `sqlite3` plus `hnswlib`. Older docs that mention ChromaDB or NetworkX as the active runtime path are outdated.
- The repo does not put a dense local LLM on the critical path.
- The checked-in experts are manifest- and dataset-driven, not generic chat weights.
- Training extras are optional until you need router, policy, or export work.

## Install Pattern

Typical local setup:

```powershell
python -m pip install -r requirements-runtime.txt -r requirements-dev.txt
python -m pip install -r requirements-training.txt
pnpm install
```

If you only need serving and tests, the training extras can be skipped.
