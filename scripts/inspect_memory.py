from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from brain.memory.graph import MemoryGraph
from brain.types import SessionId


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect memory graph contents.")
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--session-id", default="cli-session")
    args = parser.parse_args()

    graph = MemoryGraph()
    try:
        if args.query:
            result = graph.recall(args.query, limit=5, session_id=SessionId(args.session_id))
        else:
            result = graph.recall_session(SessionId(args.session_id))
        print(result)
    finally:
        graph.close()


if __name__ == "__main__":
    main()
