from __future__ import annotations

from pathlib import Path

import hnswlib  # type: ignore[import-untyped]

from ..types import MemoryNode, MemoryNodeId, Result, err, ok
from .embedder import MemoryEmbedder
from .sqlite_store import SqliteMetaStore


class ChromaVectorStore:
    def __init__(
        self,
        storage_dir: Path,
        embedder: MemoryEmbedder | None = None,
        backend_preference: str = "auto",
        sqlite_store: SqliteMetaStore | None = None,
        dimensions: int = 384,
    ) -> None:
        del backend_preference
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder or MemoryEmbedder()
        self._sqlite_store = sqlite_store or SqliteMetaStore(self._storage_dir)
        self._index_path = self._storage_dir / "memory.index"
        self._dimensions = dimensions
        self._index = hnswlib.Index(space="cosine", dim=self._dimensions)
        self._initialize_index()

    def add(self, node: MemoryNode) -> Result[None, str]:
        existing_label = self._sqlite_store.get_vector_label(node["id"])
        vector_label = self._next_label() if existing_label is None else existing_label
        self._index.add_items([list(node["embedding"])], [vector_label])
        self._sqlite_store.upsert_node(node, vector_label=vector_label)
        self._save_index()
        return ok(None)

    def search(self, query_text: str, limit: int) -> Result[list[MemoryNode], str]:
        if self.count() == 0:
            return ok([])
        query_embedding = list(self._embedder.embed(query_text))
        labels, _distances = self._index.knn_query(query_embedding, k=min(limit, self.count()))
        candidate_ids: list[MemoryNodeId] = []
        for label in labels[0]:
            node_id = self._sqlite_store.get_node_id_for_label(int(label))
            if node_id is not None:
                candidate_ids.append(node_id)
        text_ids = self._sqlite_store.search_text(query_text, limit)
        merged_ids = list(dict.fromkeys([*candidate_ids, *text_ids]))[:limit]
        return ok(self._sqlite_store.get_nodes(merged_ids))

    def get(self, node_id: MemoryNodeId) -> Result[MemoryNode, str]:
        node = self._sqlite_store.get_node(node_id)
        if node is None:
            return err(f"Unknown memory node: {node_id}")
        return ok(node)

    def delete(self, node_id: MemoryNodeId) -> Result[None, str]:
        return err("Memory deletion is not implemented in the hardened store")

    def update_access(self, node_id: MemoryNodeId) -> Result[None, str]:
        return self._sqlite_store.log_node_access(node_id)

    def all_nodes(self) -> list[MemoryNode]:
        return self._sqlite_store.list_nodes()

    def persist_node(self, node: MemoryNode) -> None:
        label = self._sqlite_store.get_vector_label(node["id"])
        if label is None:
            self.add(node)
            return
        self._sqlite_store.upsert_node(node, vector_label=label)
        self._save_index()

    def count(self) -> int:
        return len(self._sqlite_store.list_nodes())

    def backend_name(self) -> str:
        return "hnsw"

    def close(self) -> None:
        self._save_index()

    def _initialize_index(self) -> None:
        existing_nodes = self._sqlite_store.list_nodes()
        if self._index_path.exists():
            self._index.load_index(
                str(self._index_path),
                max_elements=max(len(existing_nodes), 1024),
            )
            return
        capacity = max(len(existing_nodes), 1024)
        self._index.init_index(max_elements=capacity, ef_construction=200, M=16)
        if existing_nodes:
            labels = []
            vectors = []
            for node in existing_nodes:
                label = self._sqlite_store.get_vector_label(node["id"])
                if label is None:
                    continue
                embedding = list(node["embedding"])
                if len(embedding) != self._dimensions:
                    continue
                labels.append(label)
                vectors.append(embedding)
            if labels:
                self._index.add_items(vectors, labels)
        self._index.set_ef(100)

    def _next_label(self) -> int:
        existing_nodes = self._sqlite_store.list_nodes()
        if not existing_nodes:
            return 1
        existing_labels = [
            label
            for node in existing_nodes
            if (label := self._sqlite_store.get_vector_label(node["id"])) is not None
        ]
        return max(existing_labels, default=0) + 1

    def _save_index(self) -> None:
        if self.count() == 0:
            return
        self._index.save_index(str(self._index_path))
