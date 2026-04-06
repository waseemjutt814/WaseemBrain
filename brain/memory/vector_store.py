from __future__ import annotations

from pathlib import Path
import warnings

try:
    import hnswlib  # type: ignore[import-untyped]
    _HNSWLIB_AVAILABLE = True
except ImportError:
    _HNSWLIB_AVAILABLE = False
    warnings.warn(
        "hnswlib not available - vector search disabled. "
        "Install: pip install hnswlib (requires Microsoft Visual C++ 14.0 Build Tools)",
        ImportWarning,
    )

from ..types import MemoryNode, MemoryNodeId, Result, err, ok
from .embedder import MemoryEmbedder
from .sqlite_store import SqliteMetaStore

_MIN_INDEX_CAPACITY = 1024
_DEFAULT_SEARCH_EF = 100
_INDEX_CONSTRUCTION_EF = 200
_INDEX_M = 16


class _TextOnlyVectorStore:
    """Fallback vector store that only uses SQLite FTS when hnswlib is unavailable."""
    
    def __init__(
        self,
        storage_dir: Path,
        embedder: MemoryEmbedder | None = None,
        sqlite_store: SqliteMetaStore | None = None,
        dimensions: int = 384,
    ) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder or MemoryEmbedder()
        self._sqlite_store = sqlite_store or SqliteMetaStore(self._storage_dir)
        self._dimensions = dimensions

    def add(self, node: MemoryNode) -> Result[None, str]:
        self._sqlite_store.upsert_node(node, vector_label=None)
        return ok(None)

    def search(self, query_text: str, limit: int) -> Result[list[MemoryNode], str]:
        if limit <= 0:
            return ok([])
        text_ids = self._sqlite_store.search_text(query_text, limit)
        return ok(self._sqlite_store.get_nodes(text_ids))

    def get(self, node_id: MemoryNodeId) -> Result[MemoryNode, str]:
        node = self._sqlite_store.get_node(node_id)
        if node is None:
            return err(f"Unknown memory node: {node_id}")
        return ok(node)

    def delete(self, node_id: MemoryNodeId) -> Result[None, str]:
        return err("Memory deletion is not implemented")

    def update_access(self, node_id: MemoryNodeId) -> Result[None, str]:
        return self._sqlite_store.log_node_access(node_id)

    def all_nodes(self) -> list[MemoryNode]:
        return self._sqlite_store.list_nodes()

    def persist_node(self, node: MemoryNode) -> None:
        self._sqlite_store.upsert_node(node, vector_label=None)

    def count(self) -> int:
        return len(self._sqlite_store.list_nodes())

    def backend_name(self) -> str:
        return "text-fts-only"

    def close(self) -> None:
        pass


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
        
        # Use fallback if hnswlib unavailable
        if not _HNSWLIB_AVAILABLE:
            self._impl = _TextOnlyVectorStore(storage_dir, embedder, sqlite_store, dimensions)
            return
        
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder or MemoryEmbedder()
        self._sqlite_store = sqlite_store or SqliteMetaStore(self._storage_dir)
        self._index_path = self._storage_dir / "memory.index"
        self._dimensions = dimensions
        self._index = hnswlib.Index(space="cosine", dim=self._dimensions)
        self._initialize_index()
        self._impl = None

    def add(self, node: MemoryNode) -> Result[None, str]:
        if self._impl is not None:
            return self._impl.add(node)
        existing_label = self._sqlite_store.get_vector_label(node["id"])
        vector_label = self._next_label() if existing_label is None else existing_label
        self._ensure_capacity(self._index.get_current_count() + 1)
        self._index.add_items([list(node["embedding"])], [vector_label])
        self._sqlite_store.upsert_node(node, vector_label=vector_label)
        self._save_index()
        return ok(None)

    def search(self, query_text: str, limit: int) -> Result[list[MemoryNode], str]:
        if self._impl is not None:
            return self._impl.search(query_text, limit)
        if limit <= 0:
            return ok([])
        text_ids = self._sqlite_store.search_text(query_text, limit)
        query_embedding = list(self._embedder.embed(query_text))
        candidate_ids = self._search_vector_ids(query_embedding, limit)
        merged_ids = list(dict.fromkeys([*candidate_ids, *text_ids]))[:limit]
        return ok(self._sqlite_store.get_nodes(merged_ids))

    def get(self, node_id: MemoryNodeId) -> Result[MemoryNode, str]:
        if self._impl is not None:
            return self._impl.get(node_id)
        node = self._sqlite_store.get_node(node_id)
        if node is None:
            return err(f"Unknown memory node: {node_id}")
        return ok(node)

    def delete(self, node_id: MemoryNodeId) -> Result[None, str]:
        if self._impl is not None:
            return self._impl.delete(node_id)
        return err("Memory deletion is not implemented in the hardened store")

    def update_access(self, node_id: MemoryNodeId) -> Result[None, str]:
        if self._impl is not None:
            return self._impl.update_access(node_id)
        return self._sqlite_store.log_node_access(node_id)

    def all_nodes(self) -> list[MemoryNode]:
        if self._impl is not None:
            return self._impl.all_nodes()
        return self._sqlite_store.list_nodes()

    def persist_node(self, node: MemoryNode) -> None:
        if self._impl is not None:
            self._impl.persist_node(node)
            return
        label = self._sqlite_store.get_vector_label(node["id"])
        if label is None:
            self.add(node)
            return
        self._sqlite_store.upsert_node(node, vector_label=label)
        self._save_index()

    def count(self) -> int:
        if self._impl is not None:
            return self._impl.count()
        return len(self._sqlite_store.list_nodes())

    def backend_name(self) -> str:
        if self._impl is not None:
            return self._impl.backend_name()
        return "hnsw"

    def close(self) -> None:
        if self._impl is not None:
            self._impl.close()
            return
        self._save_index()

    def _initialize_index(self) -> None:
        labels, vectors = self._collect_index_items()
        capacity = self._next_capacity(len(labels))
        if self._index_path.exists():
            try:
                self._index.load_index(str(self._index_path), max_elements=capacity)
                self._set_search_ef()
                if self._index.get_current_count() == len(labels):
                    return
            except RuntimeError:
                self._index = hnswlib.Index(space="cosine", dim=self._dimensions)
        self._rebuild_index(labels, vectors)

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
        if self._index.get_current_count() == 0:
            self._index_path.unlink(missing_ok=True)
            return
        self._index.save_index(str(self._index_path))

    def _search_vector_ids(self, query_embedding: list[float], limit: int) -> list[MemoryNodeId]:
        for attempt in range(2):
            indexed_count = self._index.get_current_count()
            if indexed_count == 0:
                return []
            query_limit = min(limit, indexed_count)
            self._set_search_ef(query_limit)
            try:
                labels, _distances = self._index.knn_query(query_embedding, k=query_limit)
            except RuntimeError:
                if attempt == 0:
                    self._rebuild_index_from_sqlite()
                    continue
                return []

            candidate_ids: list[MemoryNodeId] = []
            missing_label = False
            for label in labels[0]:
                node_id = self._sqlite_store.get_node_id_for_label(int(label))
                if node_id is None:
                    missing_label = True
                    continue
                candidate_ids.append(node_id)
            if missing_label and attempt == 0:
                self._rebuild_index_from_sqlite()
                continue
            return candidate_ids
        return []

    def _collect_index_items(self) -> tuple[list[int], list[list[float]]]:
        labels: list[int] = []
        vectors: list[list[float]] = []
        for node in self._sqlite_store.list_nodes():
            label = self._sqlite_store.get_vector_label(node["id"])
            if label is None:
                continue
            embedding = list(node["embedding"])
            if len(embedding) != self._dimensions:
                continue
            labels.append(label)
            vectors.append(embedding)
        return labels, vectors

    def _rebuild_index_from_sqlite(self) -> None:
        labels, vectors = self._collect_index_items()
        self._rebuild_index(labels, vectors)

    def _rebuild_index(self, labels: list[int], vectors: list[list[float]]) -> None:
        self._index = hnswlib.Index(space="cosine", dim=self._dimensions)
        self._index.init_index(
            max_elements=self._next_capacity(len(labels)),
            ef_construction=_INDEX_CONSTRUCTION_EF,
            M=_INDEX_M,
        )
        if labels:
            self._index.add_items(vectors, labels)
        self._set_search_ef()
        self._save_index()

    def _ensure_capacity(self, required_count: int) -> None:
        current_capacity = self._index.get_max_elements()
        if required_count <= current_capacity:
            return
        new_capacity = max(current_capacity, _MIN_INDEX_CAPACITY)
        while new_capacity < required_count:
            new_capacity *= 2
        self._index.resize_index(new_capacity)

    def _next_capacity(self, required_count: int) -> int:
        capacity = _MIN_INDEX_CAPACITY
        while capacity < required_count:
            capacity *= 2
        return capacity

    def _set_search_ef(self, query_limit: int = 0) -> None:
        self._index.set_ef(max(_DEFAULT_SEARCH_EF, query_limit))
