from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.config import load_settings
from brain.emotion.text_encoder import TextEmotionEncoder
from brain.memory.embedder import MemoryEmbedder
from brain.normalizer.voice_adapter import VoiceAdapter
from brain.runtime import WaseemBrainRuntime
from brain.types import SessionId
from scripts.runtime_client import (
    LocalRuntimeHandle,
    RuntimeDaemonClient,
    RuntimeHandleProtocol,
    is_runtime_daemon_running,
    load_runtime_daemon_state,
)

_MIN_VOICE_WARMUP_FREE_BYTES = 2 * 1024 * 1024 * 1024
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_BLUE = "\033[34m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_WHITE = "\033[37m"


@contextlib.contextmanager
def _silence_runtime_io(enabled: bool) -> Any:
    if not enabled:
        yield
        return
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        yield


def _enable_windows_ansi() -> None:
    if sys.platform != "win32" or not sys.stderr.isatty():
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-12)
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        return


def _use_color(json_only: bool) -> bool:
    return not json_only and sys.stderr.isatty() and not os.environ.get("NO_COLOR")


def _paint(text: str, *codes: str, enabled: bool) -> str:
    if not enabled or not codes:
        return text
    return "".join(codes) + text + _RESET


def _term_width() -> int:
    return max(72, min(shutil.get_terminal_size((100, 30)).columns, 120))


def _panel(title: str, lines: list[str], *, color_enabled: bool, tone: str = "accent") -> str:
    width = _term_width()
    inner = width - 4
    title_text = f" {title} "
    top = "+" + "-" + title_text + "-" * max(0, width - len(title_text) - 3) + "+"
    bottom = "+" + "-" * (width - 2) + "+"
    palette = {
        "accent": _CYAN,
        "good": _GREEN,
        "warn": _YELLOW,
        "danger": _RED,
        "muted": _BLUE,
    }
    border = palette.get(tone, _CYAN)
    body: list[str] = []
    for line in lines:
        wrapped = textwrap.wrap(line, width=inner, break_long_words=False, break_on_hyphens=False)
        for item in wrapped or [""]:
            body.append(f"| {item.ljust(inner)} |")
    rendered = [
        _paint(top, _BOLD, border, enabled=color_enabled),
        *[_paint(line, _WHITE, enabled=color_enabled) for line in body],
        _paint(bottom, _BOLD, border, enabled=color_enabled),
    ]
    return "\n".join(rendered)


def _print_prepare_banner(*, color_enabled: bool) -> None:
    width = _term_width()
    print(
        _paint("WASEEM BRAIN PREPARE".center(width), _BOLD, _CYAN, enabled=color_enabled),
        file=sys.stderr,
    )
    print(
        _paint(
            "Artifact Check | Warmup | Router | Smoke Query | Health".center(width),
            _DIM,
            _WHITE,
            enabled=color_enabled,
        ),
        file=sys.stderr,
    )
    print(_paint("=" * width, _BLUE, enabled=color_enabled), file=sys.stderr)


def _warm_models(*, include_voice: bool, quiet: bool) -> dict[str, str]:
    settings = load_settings()
    embedder = MemoryEmbedder(settings.embedding_backend, settings.embedding_model_name)
    emotion = TextEmotionEncoder()
    with _silence_runtime_io(quiet):
        embedder.embed("prepare runtime warmup text")
        emotion.encode(
            {
                "text": "prepare runtime warmup",
                "modality": "text",
                "metadata": {},
                "session_id": SessionId("prepare-runtime"),
            }
        )

    status = {
        "embedding_backend": embedder.backend_name(),
        "text_emotion": "ready",
    }
    if include_voice:
        free_bytes = shutil.disk_usage(Path.home()).free
        if free_bytes < _MIN_VOICE_WARMUP_FREE_BYTES:
            status["voice"] = (
                f"skipped: need at least 2 GiB free on {Path.home().anchor or Path.home()} "
                "for voice model cache"
            )
            return status
        adapter = VoiceAdapter(settings=settings)
        raw_audio = b"\x00\x00" * max(settings.voice_sample_rate // 4, 4000)
        with _silence_runtime_io(quiet):
            result = adapter.normalize(raw_audio)
        status["voice"] = "ready" if result["ok"] else result["error"]
    return status


def _run_python_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_router_artifact() -> dict[str, str]:
    artifact_path = ROOT / "experts" / "router.json"
    if artifact_path.exists():
        return {"status": "ready", "path": str(artifact_path)}

    result = _run_python_script("scripts/train_router.py")
    if result.returncode != 0:
        raise RuntimeError(
            f"Router artifact training failed:\n{result.stdout}\n{result.stderr}".strip()
    )
    return {"status": "trained", "path": str(artifact_path)}


def _refresh_knowledge_store(*, refresh: bool) -> dict[str, Any]:
    output_root = ROOT / "experts" / "bootstrap" / "generated"
    if output_root.exists() and not refresh:
        existing_files = sorted(output_root.rglob("*.json"))
        existing_cards = 0
        for path in existing_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            cards = payload.get("cards", [])
            if isinstance(cards, list):
                existing_cards += len(cards)
        return {
            "status": "ready",
            "output_root": str(output_root),
            "datasets": len(existing_files),
            "cards": existing_cards,
        }

    args = ["scripts/download_models.py", "--skip-model-warmup"]
    if refresh:
        args.append("--refresh-knowledge")
    result = _run_python_script(*args)
    if result.returncode != 0:
        return {
            "status": "degraded",
            "reason": (result.stdout + result.stderr).strip() or "knowledge refresh failed",
        }
    try:
        payload = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        payload = {}
    knowledge_report = payload.get("knowledge_store", {})
    if not isinstance(knowledge_report, dict):
        knowledge_report = {}
    return {
        "status": str(knowledge_report.get("status", "ready")),
        "output_root": str(knowledge_report.get("output_root", output_root)),
        "datasets": int(knowledge_report.get("datasets_written", 0)),
        "cards": int(knowledge_report.get("cards_written", 0)),
        "failed_sources": knowledge_report.get("failed_sources", []),
    }


def _maybe_train_response_policy() -> dict[str, str]:
    policy_path = ROOT / "experts" / "response-policy.json"
    if policy_path.exists():
        return {"status": "ready", "path": str(policy_path)}

    traces_dir = ROOT / "experts" / "lora" / "traces"
    trace_files = sorted(traces_dir.glob("*.jsonl"))
    trace_count = 0
    for trace_file in trace_files:
        trace_count += sum(1 for line in trace_file.read_text(encoding="utf-8").splitlines() if line)

    if trace_count < 3:
        return {
            "status": "skipped",
            "reason": "no real trace corpus yet",
            "path": str(policy_path),
        }

    result = _run_python_script("scripts/train_response_policy.py", str(traces_dir))
    if result.returncode != 0:
        raise RuntimeError(
            f"Response policy training failed:\n{result.stdout}\n{result.stderr}".strip()
        )
    return {"status": "trained", "path": str(policy_path)}


def _ensure_router_daemon() -> dict[str, str]:
    binary_path = ROOT / "target" / "debug" / ("router-daemon.exe" if sys.platform == "win32" else "router-daemon")
    args = ["scripts/manage_router_daemon.py", "start"]
    if binary_path.exists():
        args.append("--skip-build")
    result = _run_python_script(*args)
    if result.returncode != 0:
        return {
            "status": "degraded",
            "reason": (result.stdout + result.stderr).strip() or "router daemon start failed",
        }
    return {"status": "ready", "details": result.stdout.strip()}


def _ensure_runtime_daemon() -> dict[str, Any]:
    result = _run_python_script("scripts/manage_runtime_daemon.py", "start")
    if result.returncode != 0:
        return {
            "status": "degraded",
            "reason": (result.stdout + result.stderr).strip() or "runtime daemon start failed",
        }
    state = load_runtime_daemon_state() or {}
    return {
        "status": "ready",
        "details": result.stdout.strip(),
        "host": state.get("host", "127.0.0.1"),
        "port": int(state.get("port", 55881)),
        "pid": int(state.get("pid", 0)),
    }


def _local_runtime_handle() -> LocalRuntimeHandle:
    return LocalRuntimeHandle(WaseemBrainRuntime())


async def _runtime_health(
    runtime: RuntimeHandleProtocol,
    *,
    quiet: bool,
) -> dict[str, Any]:
    runtime_context = (
        _silence_runtime_io(quiet) if isinstance(runtime, LocalRuntimeHandle) else contextlib.nullcontext()
    )
    with runtime_context:
        return await runtime.health()


async def _smoke_query(
    runtime: RuntimeHandleProtocol,
    *,
    quiet: bool,
    query_text: str,
) -> dict[str, Any]:
    session_id = SessionId("prepare-smoke")
    try:
        started = time.perf_counter()
        parts: list[str] = []
        runtime_context = (
            _silence_runtime_io(quiet)
            if isinstance(runtime, LocalRuntimeHandle)
            else contextlib.nullcontext()
        )
        with runtime_context:
            async for token in runtime.query(
                query_text=query_text,
                modality="text",
                session_id=str(session_id),
            ):
                parts.append(token)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        query_result = runtime.last_query_result() or {}
        latest_trace = query_result.get("latest_trace")
        health = query_result.get("health")
        if not isinstance(health, dict):
            health = await _runtime_health(runtime, quiet=quiet)
        return {
            "response": "".join(parts).strip(),
            "elapsed_ms": round(elapsed_ms, 2),
            "response_tokens": latest_trace["response_length_tokens"]
            if isinstance(latest_trace, dict)
            else len("".join(parts).split()),
            "expert_id": str(latest_trace["expert_id"]) if isinstance(latest_trace, dict) else None,
            "response_mode": latest_trace["response_mode"] if isinstance(latest_trace, dict) else None,
            "render_strategy": latest_trace["render_strategy"] if isinstance(latest_trace, dict) else None,
            "citations_count": latest_trace["citations_count"] if isinstance(latest_trace, dict) else None,
            "confidence": round(latest_trace["confidence"], 4) if isinstance(latest_trace, dict) else None,
            "health": health,
            "runtime_mode": "daemon" if isinstance(runtime, RuntimeDaemonClient) else "local",
        }
    finally:
        await runtime.aclose()


async def _runtime_status(
    runtime: RuntimeHandleProtocol,
    *,
    quiet: bool,
) -> dict[str, Any]:
    try:
        health = await _runtime_health(runtime, quiet=quiet)
        health["runtime_mode"] = "daemon" if isinstance(runtime, RuntimeDaemonClient) else "local"
        state = load_runtime_daemon_state() if is_runtime_daemon_running() else None
        if state is not None:
            health["runtime_daemon"] = {
                "status": "ready",
                "pid": int(state.get("pid", 0)),
                "host": str(state.get("host", "127.0.0.1")),
                "port": int(state.get("port", 55881)),
                "uptime_sec": round(max(time.time() - float(state.get("started_at", time.time())), 0.0), 3),
            }
        else:
            health["runtime_daemon"] = {
                "status": "disabled" if isinstance(runtime, LocalRuntimeHandle) else "untracked",
            }
        return health
    finally:
        await runtime.aclose()


def _prepare_condition(report: dict[str, Any]) -> tuple[str, str, str]:
    issues: list[str] = []
    notes: list[str] = []
    router_artifact = report.get("router_artifact", {})
    response_policy = report.get("response_policy", {})
    knowledge_store = report.get("knowledge_store", {})
    warmup = report.get("warmup", {})
    router_daemon = report.get("router_daemon", {})
    runtime_daemon = report.get("runtime_daemon", {})
    smoke_query = report.get("smoke_query", {})
    runtime_status = report.get("runtime_status", {})

    if isinstance(knowledge_store, dict) and knowledge_store.get("status") == "degraded":
        issues.append(str(knowledge_store.get("reason", "knowledge refresh degraded")))
    if isinstance(router_artifact, dict) and router_artifact.get("status") not in {"ready", "trained"}:
        issues.append("router artifact is not ready")
    if isinstance(router_daemon, dict) and router_daemon.get("status") == "degraded":
        issues.append(str(router_daemon.get("reason", "router daemon degraded")))
    if isinstance(runtime_daemon, dict) and runtime_daemon.get("status") == "degraded":
        issues.append(str(runtime_daemon.get("reason", "runtime daemon degraded")))
    if isinstance(smoke_query, dict) and smoke_query.get("response") == "":
        issues.append("smoke query returned an empty response")
    if isinstance(warmup, dict):
        for value in warmup.values():
            lowered = str(value).lower()
            if lowered.startswith("skipped"):
                notes.append(str(value))
            elif "error" in lowered:
                issues.append(str(value))
    if isinstance(response_policy, dict) and response_policy.get("status") == "skipped":
        notes.append(str(response_policy.get("reason", "response policy skipped")))
    if isinstance(runtime_status, dict):
        notes.extend(
            [
                str(runtime_status.get("condition_summary", ""))
                for _ in [0]
                if runtime_status.get("condition") == "ready"
            ]
        )
        if runtime_status.get("condition") == "attention":
            issues.append(str(runtime_status.get("condition_summary", "runtime attention needed")))

    if issues:
        return "ATTENTION", "danger", issues[0]
    if notes:
        return "READY", "warn", notes[0]
    return "STRONG", "good", "runtime preparation completed cleanly"


def _print_prepare_summary(report: dict[str, Any], *, color_enabled: bool) -> None:
    condition, tone, summary = _prepare_condition(report)
    runtime_status = report.get("runtime_status", {})
    warmup = report.get("warmup", {})
    response_policy = report.get("response_policy", {})
    knowledge_store = report.get("knowledge_store", {})
    router_artifact = report.get("router_artifact", {})
    router_daemon = report.get("router_daemon", {})
    runtime_daemon = report.get("runtime_daemon", {})
    smoke_query = report.get("smoke_query", {})

    print(_panel("Prepare Condition", [
        "brain name       : Waseem Brain",
        f"condition        : {condition} | {summary}",
        f"router artifact  : {router_artifact.get('status', 'unknown')}",
        f"response policy  : {response_policy.get('status', 'unknown')}",
        f"knowledge store  : {knowledge_store.get('status', 'unknown')}",
    ], color_enabled=color_enabled, tone=tone), file=sys.stderr)

    if isinstance(runtime_status, dict):
        learning = runtime_status.get("learning", {})
        knowledge = runtime_status.get("knowledge", {})
        router = runtime_status.get("router", {})
        print(_panel("Runtime Snapshot", [
            f"project          : {runtime_status.get('project_name', 'Waseem Brain')}",
            f"router           : {router.get('mode', 'unknown')} | {router.get('artifact', 'unknown')} | daemon {router.get('daemon_state', 'unknown')}",
            f"experts          : {runtime_status.get('experts_available', 0)} available | {runtime_status.get('experts_loaded', 0)} loaded",
            f"memory           : {runtime_status.get('memory_node_count', 0)} nodes | backend {runtime_status.get('vector_backend', 'unknown')}",
            f"knowledge        : {knowledge.get('datasets', 0)} packs | {knowledge.get('cards', 0)} cards | {knowledge.get('seeded_cards', 0)} loaded",
            f"learning         : {learning.get('phase', 'unknown')} | traces {learning.get('trace_turns', 0)} | jobs {learning.get('training_jobs', 0)}",
        ], color_enabled=color_enabled, tone="accent"), file=sys.stderr)

    if isinstance(knowledge_store, dict):
        print(_panel("Knowledge Build", [
            f"generated packs  : {knowledge_store.get('datasets', 0)}",
            f"generated cards  : {knowledge_store.get('cards', 0)}",
            f"output root      : {knowledge_store.get('output_root', 'n/a')}",
        ], color_enabled=color_enabled, tone="muted"), file=sys.stderr)

    print(_panel("Warmup And Router", [
        f"warmup           : text={warmup.get('text_emotion', 'unknown')} | embedder={warmup.get('embedding_backend', 'unknown')} | voice={warmup.get('voice', 'not warmed')}",
        f"router daemon    : {router_daemon.get('status', 'skipped')}",
        f"runtime daemon   : {runtime_daemon.get('status', 'skipped')} | mode {runtime_status.get('runtime_mode', 'unknown')}",
    ], color_enabled=color_enabled, tone="muted"), file=sys.stderr)

    if isinstance(smoke_query, dict) and smoke_query:
        print(_panel("Smoke Query", [
            f"query result     : {smoke_query.get('response', '') or 'no response'}",
            f"expert           : {smoke_query.get('expert_id', 'n/a')} | mode {smoke_query.get('response_mode', 'n/a')} | confidence {smoke_query.get('confidence', 'n/a')}",
            f"latency          : {smoke_query.get('elapsed_ms', 'n/a')} ms | citations {smoke_query.get('citations_count', 'n/a')} | tokens {smoke_query.get('response_tokens', 'n/a')}",
        ], color_enabled=color_enabled, tone="accent"), file=sys.stderr)


def main() -> None:
    _enable_windows_ansi()
    parser = argparse.ArgumentParser(
        description="Prepare the local runtime for real CLI or HTTP usage."
    )
    parser.add_argument(
        "--include-voice",
        action="store_true",
        help="Warm the faster-whisper voice path too.",
    )
    parser.add_argument(
        "--skip-router-start",
        action="store_true",
        help="Do not start the detached router daemon during preparation.",
    )
    parser.add_argument(
        "--skip-runtime-start",
        action="store_true",
        help="Do not start or use the detached Python runtime daemon during preparation.",
    )
    parser.add_argument(
        "--skip-smoke-query",
        action="store_true",
        help="Skip the end-to-end runtime query smoke test.",
    )
    parser.add_argument(
        "--smoke-query",
        default="what is the capital of France",
        help="Text query to use for the runtime smoke test.",
    )
    parser.add_argument(
        "--verbose-warmup",
        action="store_true",
        help="Show library output during model warmup instead of silencing it.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only the JSON report on stdout without the branded stderr summary.",
    )
    parser.add_argument(
        "--skip-knowledge-refresh",
        action="store_true",
        help="Do not fetch or refresh generated online knowledge packs.",
    )
    parser.add_argument(
        "--refresh-knowledge",
        action="store_true",
        help="Force re-fetching the generated online knowledge packs.",
    )
    args = parser.parse_args()

    report: dict[str, Any] = {
        "router_artifact": _ensure_router_artifact(),
        "knowledge_store": (
            {"status": "skipped", "reason": "knowledge refresh disabled"}
            if args.skip_knowledge_refresh
            else _refresh_knowledge_store(refresh=args.refresh_knowledge)
        ),
        "response_policy": _maybe_train_response_policy(),
        "warmup": _warm_models(include_voice=args.include_voice, quiet=not args.verbose_warmup),
    }

    if not args.skip_router_start:
        report["router_daemon"] = _ensure_router_daemon()
    if not args.skip_runtime_start:
        report["runtime_daemon"] = _ensure_runtime_daemon()
    else:
        report["runtime_daemon"] = {"status": "skipped", "reason": "runtime daemon start disabled"}

    runtime: RuntimeHandleProtocol
    runtime_daemon_ready = (
        isinstance(report.get("runtime_daemon"), dict)
        and report["runtime_daemon"].get("status") == "ready"
        and is_runtime_daemon_running()
    )
    if runtime_daemon_ready:
        runtime = RuntimeDaemonClient()
    else:
        runtime = _local_runtime_handle()

    if not args.skip_smoke_query:
        report["smoke_query"] = asyncio.run(
            _smoke_query(runtime, quiet=not args.verbose_warmup, query_text=args.smoke_query)
        )
        if runtime_daemon_ready:
            runtime = RuntimeDaemonClient()
        else:
            runtime = _local_runtime_handle()

    report["runtime_status"] = asyncio.run(
        _runtime_status(runtime, quiet=not args.verbose_warmup)
    )

    if not args.json_only:
        _print_prepare_banner(color_enabled=_use_color(args.json_only))
        _print_prepare_summary(report, color_enabled=_use_color(args.json_only))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
