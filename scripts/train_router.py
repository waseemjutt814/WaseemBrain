from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.router.exporter import RouterExporter
from brain.router.trainer import RouterTrainer, RouterTrainingSample


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and export the router artifact.")
    parser.add_argument(
        "input_path",
        type=Path,
        nargs="?",
        default=ROOT / "experts" / "router-samples.jsonl",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=ROOT / "experts" / "router.json",
    )
    parser.add_argument("--feature-count", type=int, default=1024)
    args = parser.parse_args()

    if not args.input_path.exists():
        raise FileNotFoundError(f"Router training data not found: {args.input_path}")

    samples: list[RouterTrainingSample] = []
    for line in args.input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        samples.append(
            RouterTrainingSample(
                text=str(payload["text"]),
                labels=[str(label) for label in payload.get("labels", [])],
                internet_needed=bool(payload.get("internet_needed", False)),
            )
        )

    trainer = RouterTrainer(feature_count=args.feature_count)
    model = trainer.fit(samples)
    output_path = RouterExporter().export_model(args.output_path, model)
    print({"trained_samples": len(samples), "output_path": str(output_path)})


if __name__ == "__main__":
    main()
