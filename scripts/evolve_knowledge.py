from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.config import load_settings
from brain.memory.graph import MemoryGraph
from brain.types import SessionId


def _count_trace_turns(traces_dir: Path) -> int:
    total = 0
    for path in traces_dir.glob("*.jsonl"):
        try:
            total += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            continue
    return total


async def evolve_knowledge() -> None:
    settings = load_settings()
    memory = MemoryGraph(settings)
    report_path = settings.repo_root / "logs" / "knowledge_evolution_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    session_id = SessionId("knowledge-evolution")

    logger.info("Starting knowledge evolution cycle")
    try:
        before_count = memory.node_count()
        decay_result = memory.apply_decay(older_than_days=min(settings.memory_decay_days, 7))
        traces_dir = settings.lora_dir / "traces"
        trace_turns = _count_trace_turns(traces_dir) if traces_dir.exists() else 0
        trace_files = len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0

        summary = {
            "timestamp": time.time(),
            "mode": "knowledge-only",
            "before_node_count": before_count,
            "after_node_count": memory.node_count(),
            "decay_updated": decay_result["value"] if decay_result["ok"] else 0,
            "trace_files": trace_files,
            "trace_turns": trace_turns,
            "notes": [
                "No repo code was modified during evolution.",
                "Learning scope is limited to traces, policy artifacts, and memory quality.",
            ],
        }
        memory.ensure_session(session_id)
        memory.store(
            content=(
                f"Knowledge evolution snapshot: trace_files={trace_files}, trace_turns={trace_turns}, "
                f"decay_updated={summary['decay_updated']}"
            ),
            source="knowledge-evolution",
            tags=["knowledge-evolution", "audit"],
            session_id=session_id,
            source_type="session",
        )
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        logger.info(f"Knowledge evolution report written to {report_path}")
    except Exception as exc:
        logger.error(f"Knowledge evolution failed: {exc}")
        raise
    finally:
        memory.close()


if __name__ == "__main__":
    asyncio.run(evolve_knowledge())
