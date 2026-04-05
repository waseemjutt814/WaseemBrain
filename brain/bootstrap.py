from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import NotRequired, TypedDict

from .config import BrainSettings, load_settings
from .memory.graph import MemoryGraph
from .types import EvidenceReference, SessionId

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


class KnowledgeCard(TypedDict):
    id: str
    title: str
    content: str
    tags: list[str]
    source_id: NotRequired[str]
    source_label: NotRequired[str]
    source_uri: NotRequired[str]
    source_type: NotRequired[str]


class KnowledgeDataset(TypedDict):
    id: str
    name: str
    version: str
    cards: list[KnowledgeCard]


class KnowledgeSnapshot(TypedDict):
    status: str
    datasets: int
    cards: int
    seeded_cards: int
    seeded_this_run: int
    source_dir: str
    version: str
    dataset_ids: list[str]
    last_seeded_at: float
    note: str


class BuiltinKnowledgeBootstrap:
    def __init__(self, settings: BrainSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._source_dir = self._settings.expert_dir.parent / "bootstrap"

    def seed(self, memory_graph: MemoryGraph) -> KnowledgeSnapshot:
        datasets = self._load_datasets()
        snapshot = self.snapshot(memory_graph, datasets=datasets)
        if not datasets:
            return snapshot

        seeded_this_run = 0
        errors: list[str] = []
        for dataset in datasets:
            session_id = SessionId(f"bootstrap-{dataset['id']}")
            memory_graph.ensure_session(session_id)
            for card in dataset["cards"]:
                key = self._config_key(dataset["id"], card["id"])
                if memory_graph.get_config(key, "").strip():
                    continue
                result = memory_graph.store(
                    card["content"],
                    source=f"builtin-knowledge:{dataset['id']}",
                    tags=card["tags"],
                    session_id=session_id,
                    source_type="dataset",
                    citations=[self._citation_for(dataset, card)],
                )
                if not result["ok"]:
                    errors.append(f"{dataset['id']}/{card['id']}: {result['error']}")
                    continue
                memory_graph.set_config(key, str(result["value"]))
                seeded_this_run += 1

        if seeded_this_run > 0:
            memory_graph.set_config("bootstrap.knowledge.last_seeded_at", str(time.time()))
            memory_graph.set_config(
                "bootstrap.knowledge.version",
                self._version_string(datasets),
            )

        refreshed = self.snapshot(memory_graph, datasets=datasets)
        refreshed["seeded_this_run"] = seeded_this_run
        if errors:
            refreshed["status"] = "degraded"
            refreshed["note"] = errors[0]
        elif seeded_this_run > 0:
            refreshed["status"] = "seeded"
            refreshed["note"] = f"seeded {seeded_this_run} built-in knowledge cards"
        else:
            refreshed["status"] = "ready"
            refreshed["note"] = "built-in knowledge was already loaded"
        return refreshed

    def snapshot(
        self,
        memory_graph: MemoryGraph,
        *,
        datasets: list[KnowledgeDataset] | None = None,
    ) -> KnowledgeSnapshot:
        loaded_datasets = datasets if datasets is not None else self._load_datasets()
        if not loaded_datasets:
            return {
                "status": "absent",
                "datasets": 0,
                "cards": 0,
                "seeded_cards": 0,
                "seeded_this_run": 0,
                "source_dir": str(self._source_dir),
                "version": "none",
                "dataset_ids": [],
                "last_seeded_at": 0.0,
                "note": "no built-in knowledge packs were found",
            }

        seeded_cards = 0
        for dataset in loaded_datasets:
            for card in dataset["cards"]:
                if memory_graph.get_config(self._config_key(dataset["id"], card["id"]), "").strip():
                    seeded_cards += 1

        last_seeded_at_raw = memory_graph.get_config("bootstrap.knowledge.last_seeded_at", "0")
        try:
            last_seeded_at = float(last_seeded_at_raw)
        except ValueError:
            last_seeded_at = 0.0
        total_cards = sum(len(ds["cards"]) for ds in loaded_datasets)
        status = "ready" if seeded_cards == total_cards else "partial"
        note = "built-in knowledge is available"
        if status == "partial":
            note = f"built-in knowledge is only partially loaded ({seeded_cards}/{total_cards})"
        return {
            "status": status,
            "datasets": len(loaded_datasets),
            "cards": total_cards,
            "seeded_cards": seeded_cards,
            "seeded_this_run": 0,
            "source_dir": str(self._source_dir),
            "version": self._version_string(loaded_datasets),
            "dataset_ids": [dataset["id"] for dataset in loaded_datasets],
            "last_seeded_at": last_seeded_at,
            "note": note,
        }

    def _load_datasets(self) -> list[KnowledgeDataset]:
        if not self._source_dir.exists():
            return []

        datasets: list[KnowledgeDataset] = []
        for path in sorted(self._source_dir.rglob("*.json")):
            payload = self._read_json(path)
            if not isinstance(payload, dict):
                continue
            dataset_id = str(payload.get("dataset_id", path.stem)).strip() or path.stem
            name = str(payload.get("name", dataset_id)).strip() or dataset_id
            version = str(payload.get("version", "1")).strip() or "1"
            cards: list[KnowledgeCard] = []
            raw_cards = payload.get("cards", [])
            if not isinstance(raw_cards, list):
                continue
            for raw_card in raw_cards:
                if not isinstance(raw_card, dict):
                    continue
                title = str(raw_card.get("title", "")).strip()
                content = str(raw_card.get("content", "")).strip()
                if not title or not content:
                    continue
                card_id = str(raw_card.get("id", "")).strip() or _slugify(title)
                raw_tags = raw_card.get("tags", [])
                tags = (
                    [str(tag).strip() for tag in raw_tags if str(tag).strip()]
                    if isinstance(raw_tags, list)
                    else []
                )
                card: KnowledgeCard = {
                    "id": card_id,
                    "title": title,
                    "content": content,
                    "tags": tags,
                }
                source_id = str(raw_card.get("source_id", "")).strip()
                source_label = str(raw_card.get("source_label", "")).strip()
                source_uri = str(raw_card.get("source_uri", "")).strip()
                source_type = str(raw_card.get("source_type", "")).strip()
                if source_id:
                    card["source_id"] = source_id
                if source_label:
                    card["source_label"] = source_label
                if source_uri:
                    card["source_uri"] = source_uri
                if source_type:
                    card["source_type"] = source_type
                cards.append(card)
            if cards:
                datasets.append(
                    {
                        "id": dataset_id,
                        "name": name,
                        "version": version,
                        "cards": cards,
                    }
                )
        return datasets

    def _citation_for(
        self,
        dataset: KnowledgeDataset,
        card: KnowledgeCard,
    ) -> EvidenceReference:
        snippet = card["content"][:180]
        source_id = str(card.get("source_id") or f"{dataset['id']}/{card['id']}")
        source_label = str(card.get("source_label") or f"{dataset['name']}: {card['title']}")
        source_uri = str(card.get("source_uri") or f"dataset://{source_id}")
        source_type = str(card.get("source_type") or "dataset")
        return {
            "id": source_id,
            "source_type": source_type,
            "label": source_label,
            "snippet": snippet,
            "uri": source_uri,
        }

    def _config_key(self, dataset_id: str, card_id: str) -> str:
        return f"bootstrap.knowledge.card.{dataset_id}.{card_id}"

    def _version_string(self, datasets: list[KnowledgeDataset]) -> str:
        return "|".join(f"{dataset['id']}@{dataset['version']}" for dataset in datasets)

    def _read_json(self, path: Path) -> object:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None


def _slugify(text: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", text.strip().lower()).strip("-")
    return normalized or "card"
