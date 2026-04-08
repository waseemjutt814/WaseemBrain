from __future__ import annotations

import math
import time
from typing import cast
from uuid import uuid4

from ..config import BrainSettings, load_settings
from ..types import (
    EmbeddingVector,
    EvidenceReference,
    EvidenceSourceType,
    MemoryNode,
    MemoryNodeId,
    ProvenanceRecord,
    Result,
    SessionId,
    err,
    ok,
)
from .embedder import MemoryEmbedder
from .sqlite_store import SqliteMetaStore
from .vector_store import ChromaVectorStore


class MemoryGraphError(Exception):
    """Base exception for memory graph operations."""
    pass


class MemoryStoreError(MemoryGraphError):
    """Raised when memory storage fails."""
    def __init__(self, reason: str, content_preview: str = "") -> None:
        self.content_preview = content_preview[:100] if content_preview else ""
        super().__init__(f"Memory store failed: {reason}")


class MemoryGraph:
    """Memory graph with batch operations and connection pooling."""
    
    def __init__(
        self,
        settings: BrainSettings | None = None,
        vector_store: ChromaVectorStore | None = None,
        sqlite_store: SqliteMetaStore | None = None,
        embedder: MemoryEmbedder | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._sqlite_store = sqlite_store or SqliteMetaStore(self._settings.sqlite_dir)
        self._embedder = embedder or MemoryEmbedder(
            self._settings.embedding_backend,
            self._settings.embedding_model_name,
        )
        self._vector_store = vector_store or ChromaVectorStore(
            self._settings.chroma_dir,
            self._embedder,
            backend_preference=self._settings.memory_vector_backend,
            sqlite_store=self._sqlite_store,
            dimensions=self._settings.embedding_dimensions,
        )

    def close(self) -> None:
        """Close all resources including connection pool."""
        self._vector_store.close()
        self._sqlite_store.close()

    def ensure_session(self, session_id: SessionId) -> Result[None, str]:
        return self._sqlite_store.create_session(session_id)

    def node_count(self) -> int:
        return self._vector_store.count()

    def vector_backend_name(self) -> str:
        return self._vector_store.backend_name()

    def get_config(self, key: str, default: str = "") -> str:
        return self._sqlite_store.get_config(key, default)

    def set_config(self, key: str, value: str) -> Result[None, str]:
        return self._sqlite_store.set_config(key, value)

    def store(
        self,
        content: str,
        source: str,
        tags: list[str],
        session_id: SessionId,
        *,
        source_type: str = "memory",
        citations: list[EvidenceReference] | None = None,
    ) -> Result[MemoryNodeId, str]:
        del tags
        if not content.strip():
            return err("Cannot store empty memory content")
        if source_type not in {"memory", "internet", "dataset", "workspace", "session", "user"}:
            return err(f"Unsupported memory source_type: {source_type}")

        provenance: list[ProvenanceRecord] = [
            {
                "source_type": citation["source_type"],
                "source_id": citation["id"],
                "label": citation["label"],
                "uri": citation["uri"],
                "snippet": citation["snippet"],
            }
            for citation in (citations or [])
        ]
        if source_type not in {"user", "dataset", "internet", "memory"} and not provenance:
            return err("Ungrounded memory requires provenance")

        self._sqlite_store.create_session(session_id)
        self._sqlite_store.increment_query_count(session_id)
        existing = self.recall(content, limit=3, session_id=session_id)
        if not existing["ok"]:
            return err(existing["error"])

        now = time.time()
        node_id = MemoryNodeId(f"mem-{uuid4().hex}")
        node: MemoryNode = {
            "id": node_id,
            "content": content,
            "embedding": self._embedder.embed(content),
            "tags": [],
            "source": source,
            "source_type": cast(EvidenceSourceType, source_type),
            "created_at": now,
            "last_accessed": now,
            "access_count": 1,
            "confidence": 0.85 if provenance else 0.45,
            "session_id": session_id,
            "provenance": provenance or [_session_provenance(session_id, content)],
        }
        add_result = self._vector_store.add(node)
        if not add_result["ok"]:
            return add_result
        self._sqlite_store.attach_node_to_session(session_id, node_id)
        edges = [
            (
                neighbor["id"],
                self._cosine_similarity(node["embedding"], neighbor["embedding"]),
                "similar",
            )
            for neighbor in existing["value"]
            if self._cosine_similarity(node["embedding"], neighbor["embedding"]) >= 0.3
        ]
        self._sqlite_store.upsert_edges(node_id, edges)
        return ok(node_id)

    def recall(
        self,
        query: str,
        limit: int,
        session_id: SessionId | None = None,
    ) -> Result[list[MemoryNode], str]:
        vector_result = self._vector_store.search(
            query,
            max(limit, self._settings.memory_recall_limit),
        )
        if not vector_result["ok"]:
            return vector_result
        if not vector_result["value"]:
            return ok([])

        query_embedding = self._embedder.embed(query)
        seen: dict[str, MemoryNode] = {}
        for candidate in vector_result["value"]:
            seen[str(candidate["id"])] = candidate
            for neighbor_id in self._sqlite_store.get_neighbor_ids(candidate["id"], limit=2):
                neighbor = self._vector_store.get(neighbor_id)
                if neighbor["ok"]:
                    seen[str(neighbor_id)] = neighbor["value"]

        ranked = sorted(
            seen.values(),
            key=lambda node: self._score_node(query_embedding, node, session_id),
            reverse=True,
        )[:limit]
        for node in ranked:
            self._vector_store.update_access(node["id"])
        return ok(ranked)

    def recall_session(self, session_id: SessionId) -> Result[list[MemoryNode], str]:
        node_ids = self._sqlite_store.get_node_ids_for_session(session_id)
        return ok(self._sqlite_store.get_nodes(node_ids))
    
    def store_batch(
        self,
        items: list[dict[str, object]],
        session_id: SessionId,
    ) -> Result[list[MemoryNodeId], str]:
        """Store multiple memory nodes efficiently in a batch.
        
        Args:
            items: List of dicts with keys: content, source, tags, source_type, citations
            session_id: Session ID for all nodes
            
        Returns:
            Result containing list of created node IDs or error
        """
        if not items:
            return ok([])
        
        # Validate all items first
        for i, item in enumerate(items):
            content = item.get("content", "")
            if not isinstance(content, str) or not content.strip():
                return err(f"Item {i}: Cannot store empty memory content")
            source_type = item.get("source_type", "memory")
            if source_type not in {"memory", "internet", "dataset", "workspace", "session", "user"}:
                return err(f"Item {i}: Unsupported memory source_type: {source_type}")
        
        
        self._sqlite_store.create_session(session_id)
        self._sqlite_store.increment_query_count(session_id)
        
        # Batch embed all content
        contents = [str(item.get("content", "")) for item in items]
        embeddings = self._embedder.embed_batch(contents)
        
        now = time.time()
        nodes_with_labels: list[tuple[MemoryNode, int]] = []
        node_ids: list[MemoryNodeId] = []
        
        for i, (item, embedding) in enumerate(zip(items, embeddings)):
            content = str(item.get("content", ""))
            source = str(item.get("source", "unknown"))
            source_type = str(item.get("source_type", "memory"))
            citations = cast(list[EvidenceReference] | None, item.get("citations"))
            
            provenance: list[ProvenanceRecord] = [
                {
                    "source_type": citation["source_type"],
                    "source_id": citation["id"],
                    "label": citation["label"],
                    "uri": citation["uri"],
                    "snippet": citation["snippet"],
                }
                for citation in (citations or [])
            ]
            
            node_id = MemoryNodeId(f"mem-{uuid4().hex}")
            node_ids.append(node_id)
            
            node: MemoryNode = {
                "id": node_id,
                "content": content,
                "embedding": embedding,
                "tags": [],
                "source": source,
                "source_type": cast(EvidenceSourceType, source_type),
                "created_at": now,
                "last_accessed": now,
                "access_count": 1,
                "confidence": 0.85 if provenance else 0.45,
                "session_id": session_id,
                "provenance": provenance or [_session_provenance(session_id, content)],
            }
            nodes_with_labels.append((node, i))  # Use index as temporary label
        
        
        # Batch store in SQLite
        batch_result = self._sqlite_store.upsert_nodes_batch(nodes_with_labels)
        if not batch_result["ok"]:
            return batch_result
        
        
        # Attach all nodes to session
        for node_id in node_ids:
            self._sqlite_store.attach_node_to_session(session_id, node_id)
        
        
        # Add to vector store individually (no batch API available)
        for node, _ in nodes_with_labels:
            self._vector_store.add(node)
        
        
        return ok(node_ids)
    
    
    def recall_batch(
        self,
        queries: list[str],
        limit_per_query: int,
        session_id: SessionId | None = None,
    ) -> Result[list[list[MemoryNode]], str]:
        """Recall memory nodes for multiple queries efficiently.
        
        Args:
            queries: List of query strings
            limit_per_query: Maximum results per query
            session_id: Optional session for session boost
            
        Returns:
            Result containing list of result lists (one per query)
        """
        if not queries:
            return ok([])
        
        # Batch embed all queries
        query_embeddings = self._embedder.embed_batch(queries)
        
        results: list[list[MemoryNode]] = []
        for query, query_embedding in zip(queries, query_embeddings):
            vector_result = self._vector_store.search(
                query,
                max(limit_per_query, self._settings.memory_recall_limit),
            )
            if not vector_result["ok"]:
                results.append([])
                continue
            
            if not vector_result["value"]:
                results.append([])
                continue
            
            seen: dict[str, MemoryNode] = {}
            for candidate in vector_result["value"]:
                seen[str(candidate["id"])] = candidate
                for neighbor_id in self._sqlite_store.get_neighbor_ids(candidate["id"], limit=2):
                    neighbor = self._vector_store.get(neighbor_id)
                    if neighbor["ok"]:
                        seen[str(neighbor_id)] = neighbor["value"]
            
            ranked = sorted(
                seen.values(),
                key=lambda node: self._score_node(query_embedding, node, session_id),
                reverse=True,
            )[:limit_per_query]
            
            for node in ranked:
                self._vector_store.update_access(node["id"])
            
            results.append(ranked)
        
        
        return ok(results)
    
    
    def stats(self) -> dict[str, object]:
        """Return memory graph statistics for monitoring."""
        return {
            "node_count": self.node_count(),
            "vector_backend": self.vector_backend_name(),
            "embedding_cache": MemoryEmbedder.cache_stats(),
            "sqlite_pool": self._sqlite_store.pool_status(),
        }

    def apply_decay(self, older_than_days: int) -> Result[int, str]:
        decaying_nodes = self._sqlite_store.get_decaying_nodes(
            older_than_days, self._settings.memory_recall_limit
        )
        updated = 0
        # Batch get nodes for efficiency
        nodes = self._sqlite_store.get_nodes(decaying_nodes)
        for node in nodes:
            node["confidence"] = max(0.2, node["confidence"] - 0.05)
            self._vector_store.persist_node(node)
            updated += 1
        return ok(updated)

    def _score_node(
        self,
        query_embedding: EmbeddingVector,
        node: MemoryNode,
        session_id: SessionId | None,
    ) -> float:
        similarity = self._cosine_similarity(query_embedding, node["embedding"])
        recency_days = max((time.time() - node["last_accessed"]) / 86400.0, 0.0)
        recency_weight = 1.0 / (1.0 + recency_days)
        session_boost = 1.15 if session_id is not None and node["session_id"] == session_id else 1.0
        provenance_boost = 1.1 if node["provenance"] else 0.8
        return similarity * node["confidence"] * recency_weight * session_boost * provenance_boost

    def _cosine_similarity(self, left: EmbeddingVector, right: EmbeddingVector) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
        right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
        return numerator / (left_norm * right_norm)


def _session_provenance(session_id: SessionId, content: str) -> ProvenanceRecord:
    return {
        "source_type": "session",
        "source_id": str(session_id),
        "label": f"session:{session_id}",
        "uri": f"session://{session_id}",
        "snippet": content[:180],
    }
