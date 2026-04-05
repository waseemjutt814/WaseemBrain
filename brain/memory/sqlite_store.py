from __future__ import annotations

import json
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from ..types import (
    EmbeddingVector,
    EvidenceSourceType,
    MemoryNode,
    MemoryNodeId,
    ProvenanceRecord,
    Result,
    SessionId,
    ok,
)

# Older installs may have node_meta from a smaller schema; CREATE TABLE IF NOT EXISTS does not
# upgrade columns. These ALTERs bring legacy databases in line with current code.
_NODE_META_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("content", "TEXT NOT NULL DEFAULT ''"),
    ("source", "TEXT NOT NULL DEFAULT 'unknown'"),
    ("source_type", "TEXT NOT NULL DEFAULT 'internal'"),
    ("created_at", "REAL NOT NULL DEFAULT 0"),
    ("last_accessed", "REAL NOT NULL DEFAULT 0"),
    ("access_count", "INTEGER NOT NULL DEFAULT 0"),
    ("confidence", "REAL NOT NULL DEFAULT 0.5"),
    ("session_id", "TEXT NOT NULL DEFAULT ''"),
    ("embedding_json", "TEXT NOT NULL DEFAULT '[]'"),
)
_FTS_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_/-]{2,}")
_MAX_FTS_TERMS = 12


class SqliteMetaStore:
    def __init__(self, sqlite_dir: Path) -> None:
        self._sqlite_dir = Path(sqlite_dir)
        self._sqlite_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._sqlite_dir / "metadata.db"
        self._initialize()

    def create_session(self, session_id: SessionId) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                (
                    "INSERT OR IGNORE INTO sessions("
                    "id, started_at, ended_at, query_count"
                    ") VALUES(?, ?, NULL, 0)"
                ),
                (str(session_id), time.time()),
            )
        return ok(None)

    def mark_session_ended(
        self, session_id: SessionId, ended_at: float | None = None
    ) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (ended_at or time.time(), str(session_id)),
            )
        return ok(None)

    def increment_query_count(self, session_id: SessionId) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                "UPDATE sessions SET query_count = query_count + 1 WHERE id = ?",
                (str(session_id),),
            )
        return ok(None)

    def upsert_node(self, node: MemoryNode, *, vector_label: int) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO node_meta(
                    id, content, source, source_type, created_at, last_accessed,
                    access_count, confidence, session_id, vector_label, embedding_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    source = excluded.source,
                    source_type = excluded.source_type,
                    last_accessed = excluded.last_accessed,
                    access_count = excluded.access_count,
                    confidence = excluded.confidence,
                    session_id = excluded.session_id,
                    vector_label = excluded.vector_label,
                    embedding_json = excluded.embedding_json
                """,
                (
                    str(node["id"]),
                    node["content"],
                    node["source"],
                    node["source_type"],
                    node["created_at"],
                    node["last_accessed"],
                    node["access_count"],
                    node["confidence"],
                    str(node["session_id"]),
                    vector_label,
                    json.dumps(list(node["embedding"])),
                ),
            )
            connection.execute("DELETE FROM node_provenance WHERE node_id = ?", (str(node["id"]),))
            connection.execute("DELETE FROM node_search WHERE id = ?", (str(node["id"]),))
            connection.execute(
                "INSERT INTO node_search(id, content) VALUES(?, ?)",
                (str(node["id"]), node["content"]),
            )
            connection.executemany(
                """
                INSERT INTO node_provenance(node_id, source_type, source_id, label, uri, snippet)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(node["id"]),
                        record["source_type"],
                        record["source_id"],
                        record["label"],
                        record["uri"],
                        record["snippet"],
                    )
                    for record in node["provenance"]
                ],
            )
        return ok(None)

    def get_node(self, node_id: MemoryNodeId) -> MemoryNode | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, content, source, source_type, created_at, last_accessed,
                       access_count, confidence, session_id, embedding_json
                FROM node_meta
                WHERE id = ?
                """,
                (str(node_id),),
            ).fetchone()
            if row is None:
                return None
            provenance_rows = connection.execute(
                """
                SELECT source_type, source_id, label, uri, snippet
                FROM node_provenance
                WHERE node_id = ?
                ORDER BY rowid ASC
                """,
                (str(node_id),),
            ).fetchall()
        return self._row_to_node(row, provenance_rows)

    def get_nodes(self, node_ids: list[MemoryNodeId]) -> list[MemoryNode]:
        return [node for node_id in node_ids if (node := self.get_node(node_id)) is not None]

    def get_node_ids_for_session(self, session_id: SessionId) -> list[MemoryNodeId]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT node_id FROM session_nodes WHERE session_id = ?",
                (str(session_id),),
            ).fetchall()
        return [MemoryNodeId(row[0]) for row in rows]

    def get_vector_label(self, node_id: MemoryNodeId) -> int | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT vector_label FROM node_meta WHERE id = ?",
                (str(node_id),),
            ).fetchone()
        return None if row is None else int(row[0])

    def get_node_id_for_label(self, vector_label: int) -> MemoryNodeId | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id FROM node_meta WHERE vector_label = ?",
                (vector_label,),
            ).fetchone()
        return None if row is None else MemoryNodeId(str(row[0]))

    def list_nodes(self) -> list[MemoryNode]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, content, source, source_type, created_at, last_accessed,
                       access_count, confidence, session_id, embedding_json
                FROM node_meta
                ORDER BY created_at ASC
                """
            ).fetchall()
        nodes: list[MemoryNode] = []
        for row in rows:
            node = self.get_node(MemoryNodeId(str(row[0])))
            if node is not None:
                nodes.append(node)
        return nodes

    def search_text(self, query: str, limit: int) -> list[MemoryNodeId]:
        if limit <= 0 or not query.strip():
            return []
        match_query = _fts_match_query(query)
        if match_query is None:
            return []
        with self._connection() as connection:
            try:
                rows = connection.execute(
                    """
                    SELECT id
                    FROM node_search
                    WHERE node_search MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (match_query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                return []
        return [MemoryNodeId(str(row[0])) for row in rows]

    def attach_node_to_session(
        self, session_id: SessionId, node_id: MemoryNodeId
    ) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO session_nodes(session_id, node_id) VALUES(?, ?)",
                (str(session_id), str(node_id)),
            )
        return ok(None)

    def log_node_access(self, node_id: MemoryNodeId) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                (
                    "UPDATE node_meta "
                    "SET last_accessed = ?, access_count = access_count + 1 "
                    "WHERE id = ?"
                ),
                (time.time(), str(node_id)),
            )
        return ok(None)

    def get_decaying_nodes(self, older_than_days: int, max_count: int) -> list[MemoryNodeId]:
        cutoff = time.time() - (older_than_days * 86400)
        with self._connection() as connection:
            rows = connection.execute(
                (
                    "SELECT id FROM node_meta "
                    "WHERE last_accessed < ? "
                    "ORDER BY last_accessed ASC LIMIT ?"
                ),
                (cutoff, max_count),
            ).fetchall()
        return [MemoryNodeId(row[0]) for row in rows]

    def upsert_edges(
        self,
        node_id: MemoryNodeId,
        edges: list[tuple[MemoryNodeId, float, str]],
    ) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute("DELETE FROM graph_edges WHERE from_id = ?", (str(node_id),))
            connection.executemany(
                """
                INSERT INTO graph_edges(from_id, to_id, weight, relation)
                VALUES(?, ?, ?, ?)
                """,
                [
                    (str(node_id), str(neighbor_id), weight, relation)
                    for neighbor_id, weight, relation in edges
                ],
            )
        return ok(None)

    def get_neighbor_ids(self, node_id: MemoryNodeId, limit: int) -> list[MemoryNodeId]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT to_id
                FROM graph_edges
                WHERE from_id = ?
                ORDER BY weight DESC
                LIMIT ?
                """,
                (str(node_id), limit),
            ).fetchall()
        return [MemoryNodeId(str(row[0])) for row in rows]

    def get_config(self, key: str, default: str) -> str:
        with self._connection() as connection:
            row = connection.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        return default if row is None else str(row[0])

    def set_config(self, key: str, value: str) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                (
                    "INSERT INTO config(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                ),
                (key, value),
            )
        return ok(None)

    def get_ended_sessions(self, older_than_seconds: int) -> list[SessionId]:
        cutoff = time.time() - older_than_seconds
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id FROM sessions WHERE ended_at IS NOT NULL AND ended_at < ?",
                (cutoff,),
            ).fetchall()
        return [SessionId(row[0]) for row in rows]

    def log_correction_job(
        self, session_id: SessionId, expert_id: str, score: float
    ) -> Result[None, str]:
        with self._connection() as connection:
            connection.execute(
                (
                    "INSERT INTO expert_log(session_id, expert_id, score, created_at) "
                    "VALUES(?, ?, ?, ?)"
                ),
                (str(session_id), expert_id, score, time.time()),
            )
        return ok(None)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA synchronous=NORMAL;")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at REAL NOT NULL,
                    ended_at REAL,
                    query_count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS node_meta (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    vector_label INTEGER UNIQUE NOT NULL,
                    embedding_json TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS node_search USING fts5(id, content);
                CREATE TABLE IF NOT EXISTS node_provenance (
                    node_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    uri TEXT NOT NULL,
                    snippet TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS graph_edges (
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    weight REAL NOT NULL,
                    relation TEXT NOT NULL,
                    PRIMARY KEY(from_id, to_id)
                );
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_nodes (
                    session_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    UNIQUE(session_id, node_id)
                );
                CREATE TABLE IF NOT EXISTS expert_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    expert_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )
            self._migrate_node_meta_schema(connection)

    def _migrate_node_meta_schema(self, connection: sqlite3.Connection) -> None:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='node_meta'"
        ).fetchone()
        if table is None:
            return
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(node_meta)").fetchall()
        }
        for column_name, ddl in _NODE_META_COLUMN_MIGRATIONS:
            if column_name not in columns:
                connection.execute(f"ALTER TABLE node_meta ADD COLUMN {column_name} {ddl}")
                columns.add(column_name)
        if "vector_label" not in columns:
            connection.execute("ALTER TABLE node_meta ADD COLUMN vector_label INTEGER")
            columns.add("vector_label")
        self._backfill_vector_labels(connection)
        self._rebuild_node_search_fts(connection)

    def _backfill_vector_labels(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "SELECT id FROM node_meta WHERE vector_label IS NULL ORDER BY rowid ASC"
        ).fetchall()
        max_row = connection.execute(
            "SELECT COALESCE(MAX(vector_label), -1) FROM node_meta WHERE vector_label IS NOT NULL"
        ).fetchone()
        next_label = int(max_row[0]) + 1 if max_row is not None else 0
        for (node_id,) in rows:
            connection.execute(
                "UPDATE node_meta SET vector_label = ? WHERE id = ?",
                (next_label, str(node_id)),
            )
            next_label += 1

    def _rebuild_node_search_fts(self, connection: sqlite3.Connection) -> None:
        fts = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='node_search'"
        ).fetchone()
        if fts is None:
            return
        try:
            connection.execute("DELETE FROM node_search")
            connection.execute(
                "INSERT INTO node_search(id, content) SELECT id, content FROM node_meta"
            )
        except sqlite3.OperationalError:
            return

    def _row_to_node(
        self,
        row: sqlite3.Row | tuple[object, ...],
        provenance_rows: list[tuple[object, ...]],
    ) -> MemoryNode:
        embedding_values = cast(list[float], json.loads(str(row[9])))
        provenance: list[ProvenanceRecord] = [
            {
                "source_type": cast(EvidenceSourceType, str(item[0])),
                "source_id": str(item[1]),
                "label": str(item[2]),
                "uri": str(item[3]),
                "snippet": str(item[4]),
            }
            for item in provenance_rows
        ]
        return {
            "id": MemoryNodeId(str(row[0])),
            "content": str(row[1]),
            "embedding": EmbeddingVector(embedding_values),
            "tags": [],
            "source": str(row[2]),
            "source_type": cast(EvidenceSourceType, str(row[3])),
            "created_at": cast(float, row[4]),
            "last_accessed": cast(float, row[5]),
            "access_count": cast(int, row[6]),
            "confidence": cast(float, row[7]),
            "session_id": SessionId(str(row[8])),
            "provenance": provenance,
        }


def _fts_match_query(query: str) -> str | None:
    terms = list(dict.fromkeys(_FTS_TOKEN_PATTERN.findall(query.lower())))[:_MAX_FTS_TERMS]
    if not terms:
        return None
    return " OR ".join(f'"{term}"' for term in terms)
