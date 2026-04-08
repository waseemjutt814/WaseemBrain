from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FORBIDDEN_SNIPPETS = {
    "createStubGateway": "stub gateway bootstrap is forbidden in runtime code",
    "WASEEM_GATEWAY_MODE": "runtime mode toggles for stub/demo gateways are forbidden",
    "tiny-onnx": "tiny demo experts are forbidden",
    "response_prefix": "echo-style placeholder expert metadata is forbidden",
    "Fallback Expert": "placeholder expert responses are forbidden",
}

FORBIDDEN_INTERFACE_PHRASES = {
    "coming soon": "interface must not expose coming-soon placeholders",
    "todo": "interface must not ship TODO text",
    "lorem ipsum": "interface must not ship filler copy",
    "sample data": "interface must not ship sample-data promises as product features",
    "demo only": "interface must not advertise demo-only capabilities",
    "mock response": "interface must not advertise mock responses",
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

ASSISTANT_REQUIRED_SNIPPETS: dict[str, tuple[str, ...]] = {
    "interface/public/chat.html": (
        'id="transcript"',
        'id="action-list"',
        'id="assistant-ws-value"',
        'data-mode="voice"',
        'data-workspace-view="automation"',
        'data-workspace-view="memory"',
    ),
    "interface/src/web/app.ts": (
        '"/health"',
        '"/api/catalog"',
        '"/api/actions"',
        '"/ws/assistant"',
        "refreshRuntime",
        "renderWorkspaceView",
        "workspaceButtons",
    ),
    "interface/src/routes/catalog.ts": (
        "structured_session_ws_path",
        "conversation_modes",
        "voice_modes",
        'path: "/ws/assistant"',
    ),
    "interface/src/routes/actions.ts": (
        'app.get("/api/actions"',
        "ActionCatalogSchema",
    ),
    "interface/src/ws/assistant.ts": (
        'app.get("/ws/assistant"',
        '"voice.start"',
        '"voice.stop"',
        '"action.preview"',
        '"action.confirm"',
    ),
    "brain/assistant/actions.py": (
        "workspace.repo.summary",
        "workspace.repo.search",
        "verification.fast",
        "verification.project_report",
        "deployment.docker.smoke",
        "system.runtime.status",
        "system.runtime.daemon.status",
        "system.runtime.daemon.control",
        "system.firewall.inspect",
        "system.firewall.rule",
    ),
    "brain/assistant/orchestrator.py": (
        'request_type == "action.preview"',
        'request_type == "action.confirm"',
        'yield {"type": "transcript.partial"',
    ),
}


def guard_repo(root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(_scan_runtime_sources(root))
    errors.extend(_validate_registry(root))
    errors.extend(_validate_router_artifact(root))
    errors.extend(_validate_assistant_surface(root))
    return errors


def _resolve_artifact_root(base_root: Path, entry: dict[str, object]) -> Path:
    declared_root = base_root / str(entry.get("artifact_root", ""))
    if declared_root.is_dir():
        return declared_root
    if declared_root.is_file():
        return declared_root.parent
    return base_root


def _resolve_artifact_path(
    base_root: Path, entry: dict[str, object], artifact: dict[str, object]
) -> Path:
    artifact_root = _resolve_artifact_root(base_root, entry)
    candidates = [
        artifact_root / str(artifact.get("path", "")),
        base_root / str(artifact.get("path", "")),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


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

    expert_base_root = root / "experts" / "base"
    for entry in payload:
        if not isinstance(entry, dict):
            errors.append(f"{registry_path}: registry entries must be objects")
            continue
        for key in ("id", "kind", "artifact_root", "artifacts"):
            if key not in entry:
                errors.append(f"{registry_path}: missing required field {key!r} in {entry}")
        artifacts = entry.get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{registry_path}: expert {entry.get('id')} must declare artifacts")
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                errors.append(f"{registry_path}: expert {entry.get('id')} declares a non-object artifact")
                continue
            artifact_path = _resolve_artifact_path(expert_base_root, entry, artifact)
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
                errors.append(
                    f"{artifact_path}: artifact is suspiciously small ({artifact_path.stat().st_size} bytes)"
                )

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


def _validate_assistant_surface(root: Path) -> list[str]:
    errors: list[str] = []
    if not (root / "interface" / "public" / "chat.html").exists():
        return errors
    for relative_path, snippets in ASSISTANT_REQUIRED_SNIPPETS.items():
        path = root / relative_path
        if not path.exists():
            errors.append(f"{path}: required assistant surface file is missing")
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"{path}: missing required assistant contract snippet {snippet!r}")
        lowered = text.lower()
        for phrase, message in FORBIDDEN_INTERFACE_PHRASES.items():
            if phrase in lowered:
                errors.append(f"{path}: {message}")

    chat_html = root / "interface" / "public" / "chat.html"
    if chat_html.exists():
        html = chat_html.read_text(encoding="utf-8")
        if re.search(r"<article[^>]*>\s*</article>", html, flags=re.IGNORECASE):
            errors.append(f"{chat_html}: empty article cards are forbidden")
        if re.search(r"<section[^>]*>\s*</section>", html, flags=re.IGNORECASE):
            errors.append(f"{chat_html}: empty sections are forbidden")

    return errors


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

