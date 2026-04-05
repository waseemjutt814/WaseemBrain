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
    parser = argparse.ArgumentParser(description="Export a fallback JSON-backed expert artifact.")
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    args.output_path.write_text(
        json.dumps({"response_prefix": args.prefix}, indent=2), encoding="utf-8"
    )
    print(args.output_path)


if __name__ == "__main__":
    main()
