from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

from ..config import BrainSettings, load_settings
from ..types import ExpertId, Result, err, ok
from .types import ExpertArtifact, ExpertMeta


class ExpertRegistry:
    def __init__(
        self, settings: BrainSettings | None = None, registry_path: Path | None = None
    ) -> None:
        self._settings = settings or load_settings()
        self._registry_path = registry_path or self._settings.expert_registry_path
        self._entries = self._load_entries()

    def get(self, expert_id: ExpertId) -> Result[ExpertMeta, str]:
        entry = self._entries.get(str(expert_id))
        if entry is None:
            return err(f"Unknown expert id: {expert_id}")
        return ok(entry)

    def find_by_domain(self, domain: str) -> list[ExpertMeta]:
        normalized = domain.strip().lower()
        return [
            entry
            for entry in self._entries.values()
            if normalized in {item.lower() for item in entry["domains"]}
        ]

    def all(self) -> list[ExpertMeta]:
        return list(self._entries.values())

    def validate(self) -> Result[None, str]:
        if not self._entries:
            return ok(None)
        missing_files = []
        for entry in self._entries.values():
            artifact_root = self._settings.expert_dir / entry["artifact_root"]
            if not artifact_root.exists():
                missing_files.append(str(artifact_root))
                continue
            for artifact in entry["artifacts"]:
                full_path = artifact_root / artifact["path"]
                if not full_path.exists():
                    missing_files.append(str(full_path))
        if missing_files:
            return err("Missing expert files: " + ", ".join(missing_files))
        return ok(None)

    def _load_entries(self) -> dict[str, ExpertMeta]:
        if not self._registry_path.exists():
            return {}
        raw_entries = json.loads(self._registry_path.read_text(encoding="utf-8") or "[]")
        entries: dict[str, ExpertMeta] = {}
        for raw_entry in raw_entries:
            kind = str(raw_entry["kind"])
            if kind not in {"grounded-language", "repo-code", "geography-dataset"}:
                continue
            load_strategy = str(raw_entry.get("load_strategy", "lazy"))
            if load_strategy not in {"lazy", "pinned"}:
                load_strategy = "lazy"
            meta: ExpertMeta = {
                "id": ExpertId(str(raw_entry["id"])),
                "name": str(raw_entry["name"]),
                "domains": [str(item) for item in raw_entry.get("domains", [])],
                "kind": cast(
                    Literal["grounded-language", "repo-code", "geography-dataset"],
                    kind,
                ),
                "artifact_root": str(raw_entry["artifact_root"]),
                "artifacts": cast(
                    list[ExpertArtifact],
                    [
                        {
                            "name": str(item["name"]),
                            "path": str(item["path"]),
                            "kind": str(item["kind"]),
                        }
                        for item in raw_entry.get("artifacts", [])
                    ],
                ),
                "capabilities": [str(item) for item in raw_entry.get("capabilities", [])],
                "load_strategy": cast(Literal["lazy", "pinned"], load_strategy),
                "description": str(raw_entry.get("description", "")),
            }
            entries[str(meta["id"])] = meta
        return entries
