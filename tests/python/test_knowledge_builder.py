from __future__ import annotations

import shutil
from pathlib import Path

from scripts.build_knowledge_store import KnowledgeStoreBuilder, SourceSpec


def test_builder_supports_repo_local_file_sources() -> None:
    root = Path.cwd()
    temp_dir = root / ".tmp_test" / "knowledge-builder"
    temp_dir.mkdir(parents=True, exist_ok=True)
    source_path = temp_dir / "guide.md"
    source_path.write_text(
        (
            "# Temp Guide\n\n"
            "This temporary guide explains how the runtime stores grounded knowledge in local "
            "packs and then seeds those packs into memory for recall.\n\n"
            "The builder should read this Markdown file, strip noisy formatting, and emit "
            "workspace-backed cards that point back to the source path.\n\n"
            "This sentence exists to keep the content long enough for chunking and indexing "
            "without relying on placeholders or dummy filler."
        ),
        encoding="utf-8",
    )
    try:
        builder = KnowledgeStoreBuilder()
        cards = builder._build_file_cards(
            SourceSpec(
                kind="file",
                title="Temp Guide",
                path=source_path.relative_to(root).as_posix(),
                tags=["repo", "test"],
                max_chunks=2,
                max_chars=900,
            )
        )
        assert cards
        assert cards[0]["source_type"] == "workspace"
        assert cards[0]["source_uri"].startswith("workspace://")
        assert "grounded knowledge" in cards[0]["content"].lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
