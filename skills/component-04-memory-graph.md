# Component 04 Skill: Episodic Memory Graph

## Purpose
Build a hybrid memory system combining embeddings (vector similarity), graph relationships, and SQLite metadata/session tracking.

## Dependencies
- `sentence-transformers`
- `chromadb`
- `networkx`
- Python `sqlite3`

## Required Files
- `brain/memory/embedder.py`
- `brain/memory/vector_store.py`
- `brain/memory/graph_store.py`
- `brain/memory/sqlite_store.py`
- `brain/memory/graph.py`
- `tests/python/test_memory.py`

## Implementation Checklist
1. `embedder.py`:
   - Wrap model `all-MiniLM-L6-v2` (384 dim).
   - Methods: `embed(text)`, `embed_batch(texts)`.
   - Lazy singleton model loading.
   - Cache embeddings by text hash.
   - If cache size > 10,000, clear cache safely.
2. `vector_store.py`:
   - Persistent Chroma client, collection `waseem_memories`.
   - Methods:
     - `add(node)`
     - `search(query_text, limit)`
     - `get(node_id)`
     - `delete(node_id)`
     - `update_access(node_id)`
   - Generate embeddings internally with `MemoryEmbedder`.
   - Return `Result` for fallible operations.
3. `graph_store.py`:
   - Maintain directed graph with NetworkX.
   - Persist as GraphML.
   - Methods:
     - `add_node(...)`
     - `add_edge(...)`
     - `neighbors(node_id, depth)`
     - `path_between(from_id, to_id)`
     - `remove_node(node_id)`
   - Save atomically on every write (tmp + rename).
4. `sqlite_store.py`:
   - Tables: `sessions`, `node_meta`, `config`.
   - Methods:
     - `create_session(session_id) -> Result`
     - `log_node_access(node_id) -> Result`
     - `get_decaying_nodes(older_than_days, max_count) -> list[MemoryNodeId]`
     - `get_config(key, default) -> str`
     - `set_config(key, value) -> Result`
5. `graph.py` (public API):
   - `store(content, source, tags, session_id) -> Result[MemoryNodeId, str]`
     - create node, persist to all stores.
     - link top-5 similar nodes by similarity edges.
   - `recall(query, limit, session_id) -> Result[list[MemoryNode], str]`
     - vector retrieve candidates.
     - expand graph neighbors depth=1.
     - dedupe + rank by `similarity * confidence * recency_weight`.
   - `recall_session(session_id) -> Result[list[MemoryNode], str]`
   - `apply_decay(older_than_days) -> Result[int, str]`
     - lower confidence by 0.1, min 0.1.

## Test Checklist
- Store at least 5 nodes and recall relevant entries.
- Verify edges created between semantically similar/connected entries.
- Session recall returns only session-linked nodes.
- Decay lowers confidence without deleting nodes.
- Empty memory recall returns empty list, not error.

## Pass Criteria
- All stores stay consistent for create/recall/update flow.
- Ranking logic is deterministic and documented in code.
- Persistence works across process restarts (graph/sqlite/chroma).

## Premium Quality Gates (CLI)
- Static checks:
  - `python -m ruff check brain tests`
  - `python -m mypy brain`
- Targeted tests:
  - `python -m pytest tests/python/test_memory.py -q`
- Persistence sanity pass:
  - run memory tests with temp dirs and confirm graph/sqlite files are created and reused.
- Merge gate:
  - Empty recall returns `[]` with success path.
  - Decay lowers confidence but never deletes nodes.
