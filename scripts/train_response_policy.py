from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.learning.features import (
    entity_match_score,
    query_coverage_score,
    symbol_anchor_score,
)
from brain.learning.policy import ResponsePolicyExporter, ResponsePolicyTrainer
from brain.learning.types import TurnTrace
from brain.types import ExpertId, RenderStrategy, SessionId

OutcomeLiteral = Literal["answered", "memory_answered", "clarification_requested", "unsupported"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and export the offline response policy artifact from session traces."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        nargs="?",
        default=ROOT / "experts" / "lora" / "traces",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=ROOT / "experts" / "response-policy.json",
    )
    args = parser.parse_args()

    traces = _load_traces(args.input_path)
    artifact = ResponsePolicyTrainer().fit(traces)
    output_path = ResponsePolicyExporter().export_model(args.output_path, artifact)
    print({"trained_traces": len(traces), "output_path": str(output_path)})


def _load_traces(path: Path) -> list[TurnTrace]:
    trace_files = [path] if path.is_file() else sorted(path.glob("*.jsonl"))
    traces: list[TurnTrace] = []
    for trace_file in trace_files:
        for line in trace_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            query = str(payload["query"])
            response = str(payload["response"])
            traces.append(
                {
                    "session_id": SessionId(str(payload["session_id"])),
                    "expert_id": ExpertId(str(payload["expert_id"])),
                    "query": query,
                    "response": response,
                    "dialogue_intent": str(payload["dialogue_intent"]),
                    "response_mode": str(payload["response_mode"]),
                    "render_strategy": cast(
                        RenderStrategy,
                        str(payload.get("render_strategy", _default_render_strategy(payload))),
                    ),
                    "citations_count": int(payload.get("citations_count", 0)),
                    "has_next_step": bool(
                        payload.get("has_next_step", "Next useful step:" in response)
                    ),
                    "query_coverage": float(
                        payload.get("query_coverage", query_coverage_score(query, response))
                    ),
                    "entity_match_score": float(
                        payload.get("entity_match_score", entity_match_score(query, response))
                    ),
                    "symbol_anchor_score": float(
                        payload.get("symbol_anchor_score", symbol_anchor_score(query, response))
                    ),
                    "response_length_tokens": int(
                        payload.get("response_length_tokens", len(response.split()))
                    ),
                    "confidence": float(payload.get("confidence", 0.0)),
                    "decision_trace": str(payload.get("decision_trace", "")),
                    "outcome": cast(OutcomeLiteral, str(payload["outcome"])),
                    "timestamp": float(payload.get("timestamp", 0.0)),
                }
            )
    return traces


def _default_render_strategy(payload: dict[str, object]) -> str:
    response_mode = str(payload.get("response_mode", "answer"))
    outcome = str(payload.get("outcome", "answered"))
    if response_mode == "clarify":
        return "clarify"
    if outcome == "memory_answered":
        return "memory"
    if response_mode == "plan":
        return "stepwise"
    if response_mode == "unsupported" or outcome == "unsupported":
        return "unsupported"
    return "grounded"


if __name__ == "__main__":
    main()
