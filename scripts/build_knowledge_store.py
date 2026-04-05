from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.config import load_settings
from brain.internet.fetcher import ContentFetcher

_WHITESPACE_PATTERN = re.compile(r"\s+")
_PARAGRAPH_SPLIT_PATTERN = re.compile(r"(?:\r?\n){2,}")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    title: str
    tags: list[str]
    url: str | None = None
    page: str | None = None
    path: str | None = None
    max_chunks: int = 1
    max_chars: int = 900


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    name: str
    version: str
    sources: list[SourceSpec]


class KnowledgeStoreBuilder:
    def __init__(self) -> None:
        self._settings = load_settings()
        self._fetcher = ContentFetcher(settings=self._settings)

    def build(
        self,
        datasets: list[DatasetSpec],
        *,
        output_root: Path,
        refresh: bool,
        quiet: bool,
    ) -> dict[str, Any]:
        output_root.mkdir(parents=True, exist_ok=True)
        written_files: list[str] = []
        written_cards = 0
        skipped_files = 0
        failed_sources: list[str] = []
        removed_files: list[str] = []

        if refresh:
            expected_paths = {output_root / f"{dataset.dataset_id}.json" for dataset in datasets}
            for existing_path in output_root.glob("*.json"):
                if existing_path not in expected_paths:
                    existing_path.unlink(missing_ok=True)
                    removed_files.append(str(existing_path))

        for dataset in datasets:
            output_path = output_root / f"{dataset.dataset_id}.json"
            if output_path.exists() and not refresh:
                skipped_files += 1
                continue

            cards: list[dict[str, Any]] = []
            for source in dataset.sources:
                try:
                    source_cards = self._build_source_cards(source)
                    cards.extend(source_cards)
                except Exception as exc:
                    failed_sources.append(f"{dataset.dataset_id}/{source.title}: {exc}")

            payload = {
                "dataset_id": dataset.dataset_id,
                "name": dataset.name,
                "version": dataset.version,
                "cards": cards,
            }
            output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
            written_files.append(str(output_path))
            written_cards += len(cards)
            if not quiet:
                print(
                    {
                        "dataset_id": dataset.dataset_id,
                        "cards": len(cards),
                        "path": str(output_path),
                    }
                )

        return {
            "status": "ok" if not failed_sources else "partial",
            "datasets_requested": len(datasets),
            "datasets_written": len(written_files),
            "datasets_skipped": skipped_files,
            "cards_written": written_cards,
            "output_root": str(output_root),
            "failed_sources": failed_sources,
            "written_files": written_files,
            "removed_files": removed_files,
        }

    def _build_source_cards(self, source: SourceSpec) -> list[dict[str, Any]]:
        if source.kind == "url":
            return self._build_url_cards(source)
        if source.kind == "file":
            return self._build_file_cards(source)
        if source.kind == "wiki":
            return [self._build_wiki_card(source)]
        raise ValueError(f"Unsupported knowledge source kind: {source.kind}")

    def _build_url_cards(self, source: SourceSpec) -> list[dict[str, Any]]:
        if not source.url:
            raise ValueError("url source missing URL")
        fetched = self._fetcher.fetch(source.url)
        result = _run_async_result(fetched)
        if not result["ok"]:
            raise RuntimeError(result["error"])
        title = result["value"]["title"] or source.title
        chunks = _chunk_text(result["value"]["content"], max_chars=source.max_chars)
        if source.max_chunks > 0:
            chunks = chunks[: source.max_chunks]
        cards: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks, start=1):
            card_title = title if len(chunks) == 1 else f"{title} Part {index}"
            card_id = f"{_slugify(source.title)}-{index}"
            cards.append(
                {
                    "id": card_id,
                    "title": card_title,
                    "content": chunk,
                    "tags": source.tags,
                    "source_id": source.url,
                    "source_label": title,
                    "source_uri": source.url,
                    "source_type": "internet",
                }
            )
        return cards

    def _build_wiki_card(self, source: SourceSpec) -> dict[str, Any]:
        if not source.page:
            raise ValueError("wiki source missing page")
        wiki_url = f"https://en.wikipedia.org/wiki/{source.page}"
        fetched = self._fetcher.fetch(wiki_url)
        result = _run_async_result(fetched)
        if not result["ok"]:
            raise RuntimeError(result["error"])
        title = result["value"]["title"] or source.title
        chunks = _chunk_text(result["value"]["content"], max_chars=max(source.max_chars, 800))
        if not chunks:
            raise RuntimeError("wiki page returned no readable extract")
        extract = chunks[0]
        return {
            "id": _slugify(title),
            "title": title,
            "content": extract,
            "tags": source.tags,
            "source_id": source.page,
            "source_label": f"Wikipedia: {title}",
            "source_uri": wiki_url,
            "source_type": "internet",
        }

    def _build_file_cards(self, source: SourceSpec) -> list[dict[str, Any]]:
        if not source.path:
            raise ValueError("file source missing path")
        file_path = (ROOT / source.path).resolve()
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"local knowledge source not found: {file_path}")
        raw_text = file_path.read_text(encoding="utf-8")
        clean_text = _strip_markdown_noise(raw_text)
        chunks = _chunk_text(clean_text, max_chars=source.max_chars)
        if source.max_chunks > 0:
            chunks = chunks[: source.max_chunks]
        cards: list[dict[str, Any]] = []
        relative_path = file_path.relative_to(ROOT).as_posix()
        for index, chunk in enumerate(chunks, start=1):
            card_title = source.title if len(chunks) == 1 else f"{source.title} Part {index}"
            cards.append(
                {
                    "id": f"{_slugify(source.title)}-{index}",
                    "title": card_title,
                    "content": chunk,
                    "tags": source.tags,
                    "source_id": relative_path,
                    "source_label": relative_path,
                    "source_uri": f"workspace://{relative_path}",
                    "source_type": "workspace",
                }
            )
        return cards


def _run_async_result(awaitable: Any) -> Any:
    import asyncio

    return asyncio.run(awaitable)


def _chunk_text(text: str, *, max_chars: int) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    paragraphs = [
        _normalize_text(paragraph)
        for paragraph in _PARAGRAPH_SPLIT_PATTERN.split(normalized)
        if _normalize_text(paragraph)
    ]
    if not paragraphs:
        return []
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        segments = _split_long_paragraph(paragraph, max_chars=max_chars)
        chunks.extend(segments[:-1])
        current = segments[-1]
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if len(chunk) >= 180]


def _split_long_paragraph(paragraph: str, *, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = _normalize_text(sentence)
        if not sentence:
            continue
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = sentence[:max_chars]
    if current:
        chunks.append(current)
    return chunks or [paragraph[:max_chars]]


def _normalize_text(text: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def _strip_markdown_noise(text: str) -> str:
    without_code = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    without_inline = re.sub(r"`([^`]+)`", r"\1", without_code)
    without_headers = re.sub(r"^#{1,6}\s*", "", without_inline, flags=re.MULTILINE)
    without_list_markers = re.sub(r"^\s*[-*]\s+", "", without_headers, flags=re.MULTILINE)
    return without_list_markers


def _slugify(text: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", text.strip().lower()).strip("-")
    return normalized or "card"


def _load_manifest(path: Path) -> list[DatasetSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_datasets = payload.get("datasets", [])
    datasets: list[DatasetSpec] = []
    if not isinstance(raw_datasets, list):
        return datasets
    for raw_dataset in raw_datasets:
        if not isinstance(raw_dataset, dict):
            continue
        raw_sources = raw_dataset.get("sources", [])
        if not isinstance(raw_sources, list):
            continue
        sources: list[SourceSpec] = []
        for raw_source in raw_sources:
            if not isinstance(raw_source, dict):
                continue
            sources.append(
                SourceSpec(
                    kind=str(raw_source.get("kind", "")).strip(),
                    title=str(raw_source.get("title", "")).strip(),
                    url=str(raw_source.get("url", "")).strip() or None,
                    page=str(raw_source.get("page", "")).strip() or None,
                    path=str(raw_source.get("path", "")).strip() or None,
                    tags=[str(tag).strip() for tag in raw_source.get("tags", []) if str(tag).strip()],
                    max_chunks=max(int(raw_source.get("max_chunks", 1)), 1),
                    max_chars=max(int(raw_source.get("max_chars", 900)), 240),
                )
            )
        if not sources:
            continue
        datasets.append(
            DatasetSpec(
                dataset_id=str(raw_dataset.get("id", "")).strip(),
                name=str(raw_dataset.get("name", "")).strip(),
                version=str(raw_dataset.get("version", "1")).strip() or "1",
                sources=sources,
            )
        )
    return datasets


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build real local knowledge packs from curated online sources."
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=ROOT / "experts" / "knowledge-manifest.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "experts" / "bootstrap" / "generated",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-fetch and overwrite generated packs even if they already exist.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-dataset progress lines.",
    )
    args = parser.parse_args()

    datasets = _load_manifest(args.manifest_path)
    if not datasets:
        raise SystemExit(f"No valid datasets found in manifest: {args.manifest_path}")

    report = KnowledgeStoreBuilder().build(
        datasets,
        output_root=args.output_root,
        refresh=args.refresh,
        quiet=args.quiet,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
