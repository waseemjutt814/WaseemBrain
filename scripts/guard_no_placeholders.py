from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FORBIDDEN_SNIPPETS = {
    "createStubGateway": "stub gateway bootstrap is forbidden in runtime code",
    "LATTICE_GATEWAY_MODE": "runtime mode toggles for stub/demo gateways are forbidden",
    "tiny-onnx": "tiny demo experts are forbidden",
    "response_prefix": "echo-style placeholder expert metadata is forbidden",
    "Fallback Expert": "placeholder expert responses are forbidden",
}

RUNTIME_GLOBS = (
    "brain/**/*.py",
    "interface/src/**/*.ts",
    "router-daemon/src/**/*.rs",
    "scripts/coordinator_bridge.py",
    "scripts/create_expert.py",
    "scripts/train_router.py",
)

IGNORED_PATH_PARTS = {"__pycache__", "brain/router/generated"}


def guard_repo(root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(_scan_runtime_sources(root))
    errors.extend(_validate_registry(root))
    errors.extend(_validate_router_artifact(root))
    return errors


def _scan_runtime_sources(root: Path) -> list[str]:
    errors: list[str] = []
    for pattern in RUNTIME_GLOBS:
        for path in root.glob(pattern):
            normalized = path.as_posix()
            if any(part in normalized for part in IGNORED_PATH_PARTS):
                continue
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for snippet, message in FORBIDDEN_SNIPPETS.items():
                if snippet in text:
                    errors.append(f"{path}: {message}")
    return errors


def _validate_registry(root: Path) -> list[str]:
    errors: list[str] = []
    registry_path = root / "experts" / "registry.json"
    if not registry_path.exists():
        return [f"{registry_path}: missing expert registry"]
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{registry_path}: invalid JSON ({exc})"]
    if not isinstance(payload, list) or not payload:
        return [f"{registry_path}: registry must contain at least one expert"]

    for entry in payload:
        if not isinstance(entry, dict):
            errors.append(f"{registry_path}: registry entries must be objects")
            continue
        for key in ("id", "kind", "artifact_root", "artifacts"):
            if key not in entry:
                errors.append(f"{registry_path}: missing required field {key!r} in {entry}")
        artifact_root = root / "experts" / "base" / str(entry.get("artifact_root", ""))
        if not artifact_root.exists():
            errors.append(f"{artifact_root}: artifact root is missing")
            continue
        artifacts = entry.get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{registry_path}: expert {entry.get('id')} must declare artifacts")
            continue
        for artifact in artifacts:
            artifact_path = artifact_root / str(artifact.get("path", ""))
            if not artifact_path.exists():
                errors.append(f"{artifact_path}: missing declared artifact")
                continue
            lowered_name = artifact_path.name.lower()
            if any(token in lowered_name for token in ("placeholder", "demo", "tiny")):
                errors.append(f"{artifact_path}: placeholder-style artifact names are forbidden")
            if artifact_path.suffix == ".onnx":
                errors.append(f"{artifact_path}: checked-in ONNX expert artifacts are forbidden")
            minimum_size = 16
            if str(artifact.get("kind", "")).lower() == "dataset":
                minimum_size = 32
            if artifact_path.stat().st_size < minimum_size:
                errors.append(f"{artifact_path}: artifact is suspiciously small ({artifact_path.stat().st_size} bytes)")

    for onnx_path in (root / "experts").rglob("*.onnx"):
        errors.append(f"{onnx_path}: checked-in ONNX artifacts are forbidden in strict runtime mode")
    return errors


def _validate_router_artifact(root: Path) -> list[str]:
    artifact_path = root / "experts" / "router.json"
    if not artifact_path.exists():
        return [f"{artifact_path}: missing router artifact"]
    if artifact_path.stat().st_size < 128:
        return [f"{artifact_path}: router artifact is suspiciously small"]
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{artifact_path}: invalid JSON ({exc})"]
    required = {
        "labels",
        "feature_count",
        "expert_weights",
        "expert_bias",
        "internet_weights",
        "internet_bias",
        "confidence_floor",
    }
    missing = sorted(required - set(payload))
    if missing:
        return [f"{artifact_path}: missing required keys {missing}"]
    if not payload["labels"] or int(payload["feature_count"]) <= 0:
        return [f"{artifact_path}: router artifact must contain labels and positive feature_count"]
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail if runtime code or checked-in artifacts regress to placeholders."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    errors = guard_repo(args.root)
    if errors:
        print("Placeholder guard failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Placeholder guard passed for {args.root}")


if __name__ == "__main__":
    main()
