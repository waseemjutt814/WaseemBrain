from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import shutil

from brain.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a real expert manifest and artifact bundle.")
    parser.add_argument("expert_id")
    parser.add_argument("--name", required=True)
    parser.add_argument("--kind", choices=("grounded-language", "repo-code", "geography-dataset"), required=True)
    parser.add_argument("--domain", action="append", default=[])
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--description", required=True)
    parser.add_argument("--dataset", type=Path, help="Required for geography-dataset experts.")
    args = parser.parse_args()

    settings = load_settings()
    settings.expert_dir.mkdir(parents=True, exist_ok=True)
    artifact_root = settings.expert_dir / args.expert_id
    artifact_root.mkdir(parents=True, exist_ok=True)

    artifacts = [{"name": "manifest", "path": "manifest.json", "kind": "config"}]
    manifest: dict[str, object] = {
        "kind": args.kind,
        "strategy": args.kind,
    }
    if args.kind == "geography-dataset":
        if args.dataset is None or not args.dataset.exists():
            raise SystemExit("--dataset is required and must exist for geography-dataset experts")
        target_dataset = artifact_root / args.dataset.name
        shutil.copyfile(args.dataset, target_dataset)
        manifest["dataset"] = target_dataset.name
        artifacts.append({"name": "dataset", "path": target_dataset.name, "kind": "dataset"})
    elif args.kind == "repo-code":
        manifest["exclude_dirs"] = [".git", "node_modules", "dist", "target", "tmp", "data"]
    else:
        manifest["requires_evidence"] = True

    (artifact_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    registry_path = settings.expert_registry_path
    existing = json.loads(registry_path.read_text(encoding="utf-8") if registry_path.exists() else "[]")
    existing = [entry for entry in existing if entry["id"] != args.expert_id]
    existing.append(
        {
            "id": args.expert_id,
            "name": args.name,
            "domains": args.domain,
            "kind": args.kind,
            "artifact_root": args.expert_id,
            "artifacts": artifacts,
            "capabilities": args.capability,
            "load_strategy": "lazy",
            "description": args.description,
        }
    )
    registry_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print({"expert_id": args.expert_id, "artifact_root": str(artifact_root), "kind": args.kind})


if __name__ == "__main__":
    main()
