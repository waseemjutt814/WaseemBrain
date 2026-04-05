<!-- structure-author: Muhammad Waseem Akram -->

# 05 - Project Structure

This is the current source-tree map for the repo-authored parts of Lattice Brain.

## Top Level

```text
lattice-brain/
|-- brain/
|-- interface/
|-- router-daemon/
|-- experts/
|-- scripts/
|-- tests/
|-- skills/
|-- data/
|-- tmp/
|-- dist/
|-- target/
|-- README.md
|-- COMPLETE_STRUCTURE_AND_DETAILS.md
|-- PLAN.md
|-- ALGORITHMIC_BRAIN_PLAN.md
|-- run.bat
|-- pyproject.toml
|-- package.json
|-- Cargo.toml
|-- requirements-runtime.txt
|-- requirements-training.txt
|-- requirements-dev.txt
|-- requirements.txt
|-- .env.example
```

## `brain/`

```text
brain/
|-- config.py
|-- coordinator.py
|-- dialogue.py
|-- runtime.py
|-- session.py
|-- code_symbols.py
|-- types.py
|-- emotion/
|-- experts/
|-- internet/
|-- learning/
|-- memory/
|-- normalizer/
|-- router/
```

## `interface/src/`

```text
interface/src/
|-- server.ts
|-- python_gateway.ts
|-- types.ts
|-- grpc/client.ts
|-- routes/
|   |-- experts.ts
|   |-- health.ts
|   |-- memory.ts
|   `-- query.ts
|-- voice/
|   |-- player.ts
|   `-- recorder.ts
`-- ws/
    |-- handler.ts
    `-- stream.ts
```

## `router-daemon/`

```text
router-daemon/
|-- Cargo.toml
|-- build.rs
|-- proto/router.proto
`-- src/
    |-- main.rs
    |-- router.rs
    |-- expert_loader.rs
    |-- metrics.rs
    `-- session.rs
```

## `experts/`

```text
experts/
|-- registry.json
|-- router.json
|-- base/
|   |-- language-en/manifest.json
|   |-- code-general/manifest.json
|   `-- geography/
|       |-- manifest.json
|       `-- countries.json
`-- lora/
```

## `scripts/`

```text
scripts/
|-- benchmark.py
|-- chat_cli.py
|-- coordinator_bridge.py
|-- create_expert.py
|-- diagnose_backends.py
|-- download_models.py
|-- export_expert.py
|-- generate_router_stubs.py
|-- guard_no_placeholders.py
|-- init_db.py
|-- inspect_memory.py
|-- label_data.py
|-- manage_router_daemon.py
|-- prepare_runtime.py
|-- sync_codex_skills.py
|-- test_rust.ps1
|-- train_response_policy.py
`-- train_router.py
```

## `tests/`

```text
tests/
|-- python/
|   |-- support.py
|   |-- test_components.py
|   |-- test_coordinator.py
|   |-- test_emotion.py
|   |-- test_experts.py
|   |-- test_internet.py
|   |-- test_learning.py
|   |-- test_memory.py
|   |-- test_normalizer.py
|   |-- test_quality_gates.py
|   |-- test_router_grpc.py
|   |-- test_runtime_integrations.py
|   |-- test_runtime_service.py
|   |-- test_skill_sync.py
|   `-- test_types.py
`-- typescript/
    |-- python_gateway.test.ts
    |-- server.test.ts
    `-- ws.test.ts
```

## `skills/`

`skills/` contains the project-authored source markdown used to generate Codex skills. It is not the same thing as `tmp/skills/`, which is generated output.

## Generated Or Machine-Local Directories

- `data/`: SQLite DBs, memory index files, and other local runtime data
- `tmp/`: temporary outputs, generated skills, and router daemon state
- `dist/`: TypeScript build output
- `target/`: Rust build output
- `node_modules/`: Node dependencies

For deeper commentary on what these paths do, see `COMPLETE_STRUCTURE_AND_DETAILS.md`.
