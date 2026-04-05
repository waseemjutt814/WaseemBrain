from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import BrainSettings, load_settings
from ..types import ExpertId, Result, ok
from .types import TurnTrace


class ExpertCorrector:
    def __init__(self, settings: BrainSettings | None = None) -> None:
        self._settings = settings or load_settings()
        self._settings.lora_dir.mkdir(parents=True, exist_ok=True)
        self._backend_name = "offline-job-manifest"

    def backend_name(self) -> str:
        return self._backend_name

    def correct(
        self,
        expert_id: ExpertId,
        negative_examples: list[tuple[str, str]],
        *,
        positive_examples: list[tuple[str, str]] | None = None,
        turn_traces: list[TurnTrace] | None = None,
    ) -> Result[None, str]:
        dataset_dir = self._settings.lora_dir / "datasets"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = dataset_dir / f"{expert_id}.jsonl"
        dataset_lines = [
            json.dumps(
                {
                    "expert_id": str(expert_id),
                    "query": query,
                    "undesired_response": response,
                }
            )
            for query, response in negative_examples
        ]
        for query, response in positive_examples or []:
            dataset_lines.append(
                json.dumps(
                    {
                        "expert_id": str(expert_id),
                        "query": query,
                        "desired_response": response,
                    }
                )
            )
        dataset_path.write_text("\n".join(dataset_lines), encoding="utf-8")
        trace_path = self._write_expert_traces(expert_id, turn_traces or [])

        payload = {
            "expert_id": str(expert_id),
            "negative_example_count": len(negative_examples),
            "positive_example_count": len(positive_examples or []),
            "dataset_path": str(dataset_path),
            "trace_dataset_path": str(trace_path) if trace_path is not None else "",
            "created_at": time.time(),
            "backend": "offline-job-manifest",
            "status": "pending-training",
        }
        manifest_path = self._settings.lora_dir / f"{expert_id}.training-job.json"
        self._backend_name = "offline-job-manifest"
        manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return ok(None)

    def record_session_traces(
        self, session_id: str, turn_traces: list[TurnTrace]
    ) -> Result[None, str]:
        traces_dir = self._settings.lora_dir / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        trace_path = traces_dir / f"{session_id}.jsonl"
        trace_lines = [json.dumps(trace) for trace in turn_traces]
        trace_path.write_text("\n".join(trace_lines), encoding="utf-8")
        return ok(None)

    def _write_expert_traces(
        self, expert_id: ExpertId, turn_traces: list[TurnTrace]
    ) -> Path | None:
        if not turn_traces:
            return None
        traces_dir = self._settings.lora_dir / "experts"
        traces_dir.mkdir(parents=True, exist_ok=True)
        trace_path = traces_dir / f"{expert_id}.jsonl"
        trace_path.write_text(
            "\n".join(json.dumps(trace) for trace in turn_traces),
            encoding="utf-8",
        )
        return trace_path
