from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from brain.memory.sqlite_store import SqliteMetaStore
from brain.normalizer import normalize
from brain.types import EmbeddingVector, MemoryNodeId, SessionId


def _workspace_temp_dir(name: str) -> Path:
    root = Path.cwd() / ".tmp_test" / name
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_sqlite_migrates_legacy_node_meta_missing_modern_columns() -> None:
    """Older metadata.db files may predate current node_meta columns; migration must ALTER ADD."""
    with tempfile.TemporaryDirectory() as tmp:
        db_dir = Path(tmp)
        db_path = db_dir / "metadata.db"
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                """
                CREATE TABLE node_meta (
                    id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER NOT NULL,
                    confidence REAL NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

        store = SqliteMetaStore(db_dir)
        with store._connection() as active:
            column_names = {
                str(row[1])
                for row in active.execute("PRAGMA table_info(node_meta)").fetchall()
            }
        assert "content" in column_names
        assert "vector_label" in column_names
        assert store.list_nodes() == []


def test_sqlite_search_text_handles_punctuation_heavy_queries() -> None:
    root = _workspace_temp_dir("sqlite-search-text")
    try:
        store = SqliteMetaStore(root)
        store.upsert_node(
            {
                "id": MemoryNodeId("mem-fts"),
                "content": "Check python_gateway.ts first for the bridge issue.",
                "embedding": EmbeddingVector([1.0, 0.0, 0.0]),
                "tags": [],
                "source": "test",
                "source_type": "workspace",
                "created_at": 1.0,
                "last_accessed": 1.0,
                "access_count": 1,
                "confidence": 0.9,
                "session_id": SessionId("fts-session"),
                "provenance": [
                    {
                        "source_type": "workspace",
                        "source_id": "python_gateway.ts",
                        "label": "python_gateway.ts",
                        "uri": "workspace://python_gateway.ts",
                        "snippet": "Check python_gateway.ts first for the bridge issue.",
                    }
                ],
            },
            vector_label=1,
        )

        results = store.search_text(
            "Query focus: python_gateway.ts. Next useful step: inspect python_gateway.ts first.",
            5,
        )
        assert results == [MemoryNodeId("mem-fts")]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_normalize_respects_explicit_text_and_file_hints() -> None:
    text_result = normalize(
        "https://example.com",
        modality_hint="text",
        session_id=SessionId("text-session"),
    )
    assert text_result["ok"]
    assert text_result["value"]["modality"] == "text"
    assert text_result["value"]["text"] == "https://example.com"

    file_result = normalize(
        b"hello from a real file",
        modality_hint="notes.txt",
        session_id=SessionId("file-session"),
    )
    assert file_result["ok"]
    assert file_result["value"]["modality"] == "file"
    assert "hello from a real file" in file_result["value"]["text"]
