from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Append labeled router data to a JSONL file.")
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--text", required=True)
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument("--internet-needed", action="store_true")
    args = parser.parse_args()
    payload = {"text": args.text, "labels": args.label, "internet_needed": args.internet_needed}
    with args.output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    print(payload)


if __name__ == "__main__":
    main()
