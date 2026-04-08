from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Protocol

try:
    import hnswlib as imported_hnswlib  # type: ignore[import-untyped]
except ImportError:
    imported_hnswlib = None

_HNSWLIB_AVAILABLE = imported_hnswlib is not None

from ..types import EmbeddingVector, MemoryNode, MemoryNodeId, Result, err, ok
from .embedder import MemoryEmbedder
from .sqlite_store import SqliteMetaStore

_MIN_INDEX_CAPACITY = 1024
_DEFAULT_SEARCH_EF = 100
_INDEX_CONSTRUCTION_EF = 200
_INDEX_M = 16
_TEXT_BACKEND_ALIASES = {"text", "fts", "sqlite", "text-fts-only"}


class _IndexProtocol(Protocol):
    def init_index(self, *, max_elements: int, ef_construction: int, m: int) -> None: ...

    def load_index(self, path: str, *, max_elements: int) -> None: ...

    def save_index(self, path: str) -> None: ...

    def add_items(self, vectors: list[list[float]], labels: list[int]) -> None: ...

    def knn_query(self, vector: list[float], *, k: int) -> tuple[list[list[int]], list[list[float]]]: ...

    def get_current_count(self) -> int: ...

    def get_max_elements(self) -> int: ...

    def resize_index(self, max_elements: int) -> None: ...

    def set_ef(self, value: int) -> None: ...


class _NativeHnswIndex:
    def __init__(self, dimensions: int) -> None:
        assert imported_hnswlib is not None
        self._index = imported_hnswlib.Index(space="cosine", dim=dimensions)

    def init_index(self, *, max_elements: int, ef_construction: int, m: int) -> None:
        self._index.init_index(max_elements=max_elements, ef_construction=ef_construction, M=m)

    def load_index(self, path: str, *, max_elements: int) -> None:
        self._index.load_index(path, max_elements=max_elements)

    def save_index(self, path: str) -> None:
        self._index.save_index(path)

    def add_items(self, vectors: list[list[float]], labels: list[int]) -> None:
        self._index.add_items(vectors, labels)

    def knn_query(self, vector: list[float], *, k: int) -> tuple[list[list[int]], list[list[float]]]:
        labels, distances = self._index.knn_query(vector, k=k)
        return [list(row) for row in labels], [list(row) for row in distances]

    def get_current_count(self) -> int:
        return int(self._index.get_current_count())

    def get_max_elements(self) -> int:
        return int(self._index.get_max_elements())

    def resize_index(self, max_elements: int) -> None:
        self._index.resize_index(max_elements)

    def set_ef(self, value: int) -> None:
        self._index.set_ef(value)


class _PortableHnswIndex:
    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions
        self._max_elements = _MIN_INDEX_CAPACITY
        self._vectors: dict[int, list[float]] = {}

    def init_index(self, *, max_elements: int, ef_construction: int, m: int) -> None:
        del ef_construction, m
        self._max_elements = max(max_elements, _MIN_INDEX_CAPACITY)
        self._vectors = {}

    def load_index(self, path: str, *, max_elements: int) -> None:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"failed to load portable index: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("portable index payload must be a JSON object")
        dimensions = int(payload.get("dimensions", self._dimensions))
        if dimensions != self._dimensions:
            raise RuntimeError(
                f"portable index dimensions mismatch: expected {self._dimensions}, got {dimensions}"
            )
        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list):
            raise RuntimeError("portable index records must be a list")
        records: dict[int, list[float]] = {}
        for item in raw_records:
            if not isinstance(item, dict):
                raise RuntimeError("portable index record must be a dict")
            label = int(item["label"])
            vector = [float(value) for value in item["vector"]]
            if len(vector) != self._dimensions:
                raise RuntimeError(
                    f"portable index vector dimensions mismatch for label {label}: {len(vector)}"
                )
            records[label] = vector
        self._vectors = records
        stored_max = int(payload.get("max_elements", len(records) or _MIN_INDEX_CAPACITY))
        self._max_elements = max(stored_max, max_elements, len(records), _MIN_INDEX_CAPACITY)

    def save_index(self, path: str) -> None:
        payload = {
            "dimensions": self._dimensions,
            "max_elements": self._max_elements,
            "records": [
                {"label": label, "vector": vector}
                for label, vector in sorted(self._vectors.items())
            ],
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_items(self, vectors: list[list[float]], labels: list[int]) -> None:
        for vector, label in zip(vectors, labels, strict=True):
            if len(vector) != self._dimensions:
                raise RuntimeError(
                    f"portable index vector dimensions mismatch: {len(vector)} != {self._dimensions}"
                )
            new_count = len(self._vectors) + (0 if label in self._vectors else 1)
            if new_count > self._max_elements:
                raise RuntimeError(
                    f"portable index capacity exceeded: {new_count} > {self._max_elements}"
                )
            self._vectors[int(label)] = [float(value) for value in vector]

    def knn_query(self, vector: list[float], *, k: int) -> tuple[list[list[int]], list[list[float]]]:
        scored = sorted(
            self._vectors.items(),
            key=lambda item: _cosine_similarity(vector, item[1]),
            reverse=True,
        )[:k]
        labels = [[label for label, _ in scored]]
        distances = [[1.0 - _cosine_similarity(vector, values) for _, values in scored]]
        return labels, distances

    def get_current_count(self) -> int:
        return len(self._vectors)

    def get_max_elements(self) -> int:
        return self._max_elements

    def resize_index(self, max_elements: int) -> None:
        self._max_elements = max(max_elements, len(self._vectors), _MIN_INDEX_CAPACITY)

    def set_ef(self, value: int) -> None:
        del value


class _TextOnlyVectorStore:
    """Fallback vector store that only uses SQLite FTS."""

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
        vector_label = self._next_label()
        self._sqlite_store.upsert_node(node, vector_label=vector_label)
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
        del node_id
        return err("Memory deletion is not implemented")

    def update_access(self, node_id: MemoryNodeId) -> Result[None, str]:
        return self._sqlite_store.log_node_access(node_id)

    def all_nodes(self) -> list[MemoryNode]:
        return self._sqlite_store.list_nodes()

    def persist_node(self, node: MemoryNode) -> None:
        label = self._sqlite_store.get_vector_label(node["id"])
        if label is None:
            label = self._next_label()
        self._sqlite_store.upsert_node(node, vector_label=label)

    def count(self) -> int:
        return len(self._sqlite_store.list_nodes())

    def backend_name(self) -> str:
        return "text-fts-only"

    def close(self) -> None:
        return None

    def _next_label(self) -> int:
        labels = [
            label
            for node in self._sqlite_store.list_nodes()
            if (label := self._sqlite_store.get_vector_label(node["id"])) is not None
        ]
        return max(labels, default=0) + 1


class ChromaVectorStore:
    def __init__(
        self,
        storage_dir: Path,
        embedder: MemoryEmbedder | None = None,
        backend_preference: str = "auto",
        sqlite_store: SqliteMetaStore | None = None,
        dimensions: int = 384,
    ) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder or MemoryEmbedder()
        self._sqlite_store = sqlite_store or SqliteMetaStore(self._storage_dir)
        self._index_path = self._storage_dir / "memory.index"
        self._dimensions = dimensions
        self._backend_preference = backend_preference.strip().lower() or "auto"
        self._impl: _TextOnlyVectorStore | None = None

        if self._backend_preference in _TEXT_BACKEND_ALIASES:
            self._impl = _TextOnlyVectorStore(
                self._storage_dir,
                self._embedder,
                self._sqlite_store,
                dimensions,
            )
            return

        self._index: _IndexProtocol = _create_index(self._dimensions)
        self._initialize_index()

    def add(self, node: MemoryNode) -> Result[None, str]:
        if self._impl is not None:
            return self._impl.add(node)
        existing_label = self._sqlite_store.get_vector_label(node["id"])
        if existing_label is not None:
            self._sqlite_store.upsert_node(node, vector_label=existing_label)
            self._rebuild_index_from_sqlite()
            return ok(None)
        vector_label = self._next_label()
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
        del node_id
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
        self._rebuild_index_from_sqlite()

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
                self._index = _create_index(self._dimensions)
        self._rebuild_index(labels, vectors)

    def _next_label(self) -> int:
        existing_labels = [
            label
            for node in self._sqlite_store.list_nodes()
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
        self._index = _create_index(self._dimensions)
        self._index.init_index(
            max_elements=self._next_capacity(len(labels)),
            ef_construction=_INDEX_CONSTRUCTION_EF,
            m=_INDEX_M,
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


def _create_index(dimensions: int) -> _IndexProtocol:
    if _HNSWLIB_AVAILABLE:
        return _NativeHnswIndex(dimensions)
    return _PortableHnswIndex(dimensions)


def _cosine_similarity(left: list[float], right: list[float] | EmbeddingVector) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return numerator / (left_norm * right_norm)




