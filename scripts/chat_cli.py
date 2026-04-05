from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import os
import shutil
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.config import BrainSettings, load_settings
from brain.emotion.text_encoder import TextEmotionEncoder
from brain.experts.registry import ExpertRegistry
from brain.memory.embedder import MemoryEmbedder
from brain.normalizer.voice_adapter import VoiceAdapter
from brain.types import SessionId
from scripts.runtime_client import (
    LocalRuntimeHandle,
    RuntimeDaemonClient,
    RuntimeHandleProtocol,
    is_runtime_daemon_running,
    load_runtime_daemon_state,
)

_MIN_VOICE_WARMUP_FREE_BYTES = 2 * 1024 * 1024 * 1024
_PIPELINE_LABEL = "normalize > emotion > route > memory > experts > render"
_SPINNER_FRAMES = ("|", "/", "-", "\\")
_SPINNER_STEPS = (
    "reading input",
    "normalizing signal",
    "routing query",
    "checking memory",
    "assembling response",
)
_WORDMARK = (
    "W   W  AAAAA  SSSSS  EEEEE  EEEEE  M   M        BBBB   RRRR    AAAAA  III  N   N",
    "W   W  A   A  S      E      E      MM MM        B   B  R   R   A   A   I   NN  N",
    "W W W  AAAAA  SSSSS  EEEEE  EEEEE  M M M        BBBB   RRRR    AAAAA   I   N N N",
    "WW WW  A   A      S  E      E      M   M        B   B  R R     A   A   I   N  NN",
    "W   W  A   A  SSSSS  EEEEE  EEEEE  M   M        BBBB   R  RR   A   A  III  N   N",
)

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
    if sys.platform != "win32" or not sys.stdout.isatty():
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        return


def _use_color(plain_ui: bool) -> bool:
    return not plain_ui and sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _paint(text: str, *codes: str, enabled: bool) -> str:
    if not enabled or not codes:
        return text
    return "".join(codes) + text + _RESET


def _term_width() -> int:
    return max(72, min(shutil.get_terminal_size((100, 30)).columns, 120))


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _count_jsonl_lines(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            total += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            continue
    return total


def _format_age(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def _clear_screen(*, color_enabled: bool) -> None:
    if color_enabled:
        sys.stdout.write("\033[2J\033[H")
    else:
        sys.stdout.write("\n" * 6)
    sys.stdout.flush()


def _print_banner(*, color_enabled: bool) -> None:
    width = _term_width()
    colors = (_CYAN, _BLUE, _CYAN, _GREEN, _BLUE)
    print()
    for line, color in zip(_WORDMARK, colors, strict=True):
        print(_paint(line.center(width), _BOLD, color, enabled=color_enabled))
    subtitle = "Waseem Brain Terminal | Runtime | Memory | Experts | Learning"
    print(_paint(subtitle.center(width), _DIM, _WHITE, enabled=color_enabled))
    print(_paint("=" * width, _BLUE, enabled=color_enabled))


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


def _warm_models(*, include_voice: bool, quiet: bool) -> dict[str, str]:
    settings = load_settings()
    embedder = MemoryEmbedder(settings.embedding_backend, settings.embedding_model_name)
    emotion = TextEmotionEncoder()
    with _silence_runtime_io(quiet):
        embedder.embed("warmup text for memory search")
        emotion.encode(
            {
                "text": "warmup text",
                "modality": "text",
                "metadata": {},
                "session_id": SessionId("cli-warmup"),
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


def _resolve_query_input(modality: str, raw_value: str) -> tuple[object, str]:
    if modality == "text":
        return raw_value, "text"
    if modality == "url":
        return raw_value, "url"
    path = Path(raw_value).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    raw_bytes = path.read_bytes()
    if modality == "voice":
        return raw_bytes, "voice"
    return raw_bytes, path.name


async def _collect_snapshot(
    runtime: RuntimeHandleProtocol,
    *,
    settings: BrainSettings,
    session_id: SessionId,
    warm_status: dict[str, str] | None,
) -> dict[str, Any]:
    health = await runtime.health()
    registry = ExpertRegistry(settings=settings)
    registry_validation = registry.validate()
    experts = registry.all()
    router_state = _read_json(ROOT / "tmp" / "router-daemon" / "state.json")
    runtime_daemon_state = load_runtime_daemon_state() if is_runtime_daemon_running() else None
    response_policy_path = settings.expert_dir.parent / "response-policy.json"
    trace_dir = settings.lora_dir / "traces"
    expert_trace_dir = settings.lora_dir / "experts"
    dataset_dir = settings.lora_dir / "datasets"
    trace_files = sorted(trace_dir.glob("*.jsonl")) if trace_dir.exists() else []
    expert_trace_files = sorted(expert_trace_dir.glob("*.jsonl")) if expert_trace_dir.exists() else []
    dataset_files = sorted(dataset_dir.glob("*.jsonl")) if dataset_dir.exists() else []
    training_jobs = sorted(settings.lora_dir.glob("*.training-job.json"))

    condition_lookup = {
        "attention": ("ATTENTION", "danger"),
        "ready": ("READY", "warn"),
        "strong": ("STRONG", "good"),
    }
    condition, condition_tone = condition_lookup.get(
        str(health.get("condition", "ready")).lower(),
        ("READY", "warn"),
    )
    summary = str(health.get("condition_summary", "runtime status unavailable"))
    if warm_status is not None:
        for value in warm_status.values():
            lowered = str(value).lower()
            if "error" in lowered:
                condition = "ATTENTION"
                condition_tone = "danger"
                summary = str(value)
                break
            if lowered.startswith("skipped") and condition == "STRONG":
                condition = "READY"
                condition_tone = "warn"
                summary = str(value)

    router_snapshot = health.get("router", {})
    router_line = (
        f"{settings.router_backend} | artifact {health['components']['router_artifact']} "
        f"| daemon {router_snapshot.get('daemon_state', 'unknown')}"
    )
    if router_state is not None:
        started_at = float(router_state.get("started_at", time.time()))
        router_line += (
            f" | daemon pid {router_state.get('pid', '?')} "
            f"port {router_state.get('port', settings.grpc_port)} "
            f"| uptime {_format_age(max(time.time() - started_at, 0.0))}"
        )
    elif settings.router_backend == "local":
        router_line += " | local artifact mode"
    else:
        router_line += " | daemon state unavailable"
    if isinstance(router_snapshot, dict) and router_snapshot.get("last_error"):
        router_line += f" | note {router_snapshot['last_error']}"

    return {
        "health": health,
        "learning": health.get("learning", {}),
        "knowledge": health.get("knowledge", {}),
        "condition": condition,
        "condition_tone": condition_tone,
        "summary": summary,
        "session_id": str(session_id),
        "router_line": router_line,
        "runtime_daemon_line": (
            "local in-process runtime"
            if runtime_daemon_state is None
            else (
                f"hot daemon pid {runtime_daemon_state.get('pid', '?')} "
                f"| {runtime_daemon_state.get('host', '127.0.0.1')}:{runtime_daemon_state.get('port', '?')}"
            )
        ),
        "expert_ids": [str(entry["id"]) for entry in experts],
        "expert_count": len(experts),
        "trace_files": len(trace_files),
        "trace_turns": _count_jsonl_lines(trace_files),
        "expert_trace_files": len(expert_trace_files),
        "expert_trace_turns": _count_jsonl_lines(expert_trace_files),
        "dataset_files": len(dataset_files),
        "training_jobs": len(training_jobs),
        "response_policy": "ready" if response_policy_path.exists() else "rule-default",
        "embedding_backend": warm_status.get("embedding_backend", settings.embedding_backend)
        if warm_status is not None
        else settings.embedding_backend,
        "text_emotion": warm_status.get("text_emotion", "unknown") if warm_status is not None else "unknown",
        "voice": warm_status.get("voice", "not warmed") if warm_status is not None else "not warmed",
        "sqlite_path": _relative_path(settings.sqlite_dir / "metadata.db"),
        "index_path": _relative_path(settings.vector_index_path),
    }


async def _print_dashboard(
    runtime: RuntimeHandleProtocol,
    *,
    settings: BrainSettings,
    session_id: SessionId,
    warm_status: dict[str, str] | None,
    color_enabled: bool,
) -> None:
    snapshot = await _collect_snapshot(
        runtime,
        settings=settings,
        session_id=session_id,
        warm_status=warm_status,
    )
    print(
        _panel(
            "Project Condition",
            [
                "brain name       : Waseem Brain",
                f"condition        : {snapshot['condition']} | {snapshot['summary']}",
                f"session          : {snapshot['session_id']}",
                f"pipeline         : {_PIPELINE_LABEL}",
            ],
            color_enabled=color_enabled,
            tone=str(snapshot["condition_tone"]),
        )
    )
    print(
        _panel(
            "Runtime Status",
            [
                f"router           : {snapshot['router_line']}",
                (
                "memory           : "
                    f"{snapshot['health']['memory_node_count']} nodes | "
                    f"backend {snapshot['health']['vector_backend']} | "
                    f"index {snapshot['index_path']}"
                ),
                f"runtime daemon   : {snapshot['runtime_daemon_line']}",
                (
                    "experts          : "
                    f"{snapshot['expert_count']} available | "
                    f"{snapshot['health']['experts_loaded']} loaded | "
                    f"max {settings.expert_max_loaded}"
                ),
                f"expert ids       : {', '.join(snapshot['expert_ids']) or 'none'}",
                (
                    "internet         : "
                    f"{snapshot['health']['components']['internet']} | "
                    f"max {settings.internet_max_requests_per_query} requests per query"
                ),
                (
                    "warmup           : "
                    f"text={snapshot['text_emotion']} | embedder={snapshot['embedding_backend']} "
                    f"| voice={snapshot['voice']}"
                ),
            ],
            color_enabled=color_enabled,
            tone="accent",
        )
    )
    knowledge = snapshot["knowledge"]
    learning_phase = (
        str(snapshot["learning"].get("phase", "unknown")) if settings.learning_enabled else "disabled"
    )
    print(
        _panel(
            "Learning Status",
            [
                (
                    "built-in knowledge: "
                    f"{knowledge.get('datasets', 0)} packs | "
                    f"{knowledge.get('cards', 0)} cards | "
                    f"{knowledge.get('seeded_cards', 0)} loaded"
                ),
                f"learning         : {'enabled' if settings.learning_enabled else 'disabled'} | backend {settings.learning_backend}",
                f"response policy  : {snapshot['response_policy']}",
                f"trace corpus     : {snapshot['trace_files']} session files | {snapshot['trace_turns']} turns",
                f"expert traces    : {snapshot['expert_trace_files']} files | {snapshot['expert_trace_turns']} turns",
                (
                    "training jobs    : "
                    f"{snapshot['training_jobs']} pending manifests | "
                    f"{snapshot['dataset_files']} datasets | "
                    f"trained traces {snapshot['learning'].get('trained_trace_count', 0)}"
                ),
                f"learning phase   : {learning_phase}",
                f"last learning    : {snapshot['learning'].get('last_event', 'n/a')}",
            ],
            color_enabled=color_enabled,
            tone="muted",
        )
    )
    print(
        _panel(
            "Commands",
            [
                "/status or /dashboard : full branded runtime dashboard",
                "/learning             : learning-only status panel",
                "/project              : project condition summary",
                "/health               : raw runtime health snapshot",
                "/experts              : currently loaded expert ids",
                "/recall <text>        : inspect memory recall results",
                "/clear                : redraw the Waseem Brain screen",
                "/quit                 : exit the terminal chat",
            ],
            color_enabled=color_enabled,
            tone="accent",
        )
    )


async def _print_project_status(
    runtime: RuntimeHandleProtocol,
    *,
    settings: BrainSettings,
    session_id: SessionId,
    warm_status: dict[str, str] | None,
    color_enabled: bool,
) -> None:
    snapshot = await _collect_snapshot(
        runtime,
        settings=settings,
        session_id=session_id,
        warm_status=warm_status,
    )
    print(
        _panel(
            "Project Condition",
            [
                f"condition        : {snapshot['condition']} | {snapshot['summary']}",
                f"router backend   : {snapshot['health']['router_backend']}",
                f"memory backend   : {snapshot['health']['vector_backend']}",
                f"policy mode      : {snapshot['response_policy']}",
                f"available experts: {snapshot['expert_count']}",
                f"knowledge packs  : {snapshot['knowledge'].get('datasets', 0)} | cards {snapshot['knowledge'].get('cards', 0)}",
                f"runtime mode     : {snapshot['runtime_daemon_line']}",
            ],
            color_enabled=color_enabled,
            tone=str(snapshot["condition_tone"]),
        )
    )


async def _print_learning_status(
    runtime: RuntimeHandleProtocol,
    *,
    settings: BrainSettings,
    session_id: SessionId,
    warm_status: dict[str, str] | None,
    color_enabled: bool,
) -> None:
    snapshot = await _collect_snapshot(
        runtime,
        settings=settings,
        session_id=session_id,
        warm_status=warm_status,
    )
    print(
        _panel(
            "Learning Status",
            [
                f"learning enabled : {'yes' if settings.learning_enabled else 'no'}",
                f"knowledge status : {snapshot['knowledge'].get('status', 'unknown')}",
                f"knowledge cards  : {snapshot['knowledge'].get('cards', 0)}",
                f"response policy  : {snapshot['response_policy']}",
                f"trace files      : {snapshot['trace_files']}",
                f"trace turns      : {snapshot['trace_turns']}",
                f"expert trace     : {snapshot['expert_trace_files']} files | {snapshot['expert_trace_turns']} turns",
                f"training jobs    : {snapshot['training_jobs']}",
                f"datasets         : {snapshot['dataset_files']}",
                f"trained traces   : {snapshot['learning'].get('trained_trace_count', 0)}",
                f"last event       : {snapshot['learning'].get('last_event', 'n/a')}",
            ],
            color_enabled=color_enabled,
            tone="muted",
        )
    )


async def _spinner(label: str, *, color_enabled: bool, stop: asyncio.Event) -> None:
    width = _term_width()
    index = 0
    while not stop.is_set():
        frame = _SPINNER_FRAMES[index % len(_SPINNER_FRAMES)]
        step = _SPINNER_STEPS[index % len(_SPINNER_STEPS)]
        line = _paint(f"{label} {_PIPELINE_LABEL} | {step} {frame}", _DIM, _CYAN, enabled=color_enabled)
        sys.stdout.write("\r" + line.ljust(width))
        sys.stdout.flush()
        index += 1
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.12)
        except TimeoutError:
            continue
    sys.stdout.write("\r" + (" " * width) + "\r")
    sys.stdout.flush()


def _print_metrics(metrics: dict[str, Any], *, json_mode: bool, color_enabled: bool) -> None:
    if json_mode:
        print(json.dumps(metrics, indent=2))
        return
    tone = "good" if metrics.get("outcome") in {"answered", "memory_answered"} else "warn"
    print(
        _panel(
            "Brain Activity",
            [
                f"pipeline         : {_PIPELINE_LABEL}",
                f"result           : {metrics.get('outcome', 'unknown')} | mode {metrics.get('response_mode', 'n/a')}",
                f"expert           : {metrics.get('expert_id', 'n/a')} | render {metrics.get('render_strategy', 'n/a')}",
                f"quality          : confidence {metrics.get('confidence', 'n/a')} | citations {metrics.get('citations_count', 'n/a')} | tokens {metrics.get('response_tokens', 'n/a')}",
                f"decision trace   : {metrics.get('decision_trace', 'n/a')}",
            ],
            color_enabled=color_enabled,
            tone=tone,
        )
    )


async def _run_turn(
    runtime: RuntimeHandleProtocol,
    *,
    query_text: str,
    modality: str,
    session_id: SessionId,
    show_metrics: bool,
    json_metrics: bool,
    color_enabled: bool,
    plain_ui: bool,
    quiet_runtime_io: bool,
) -> int:
    raw_input, modality_hint = _resolve_query_input(modality, query_text)
    started = time.perf_counter()
    response_parts: list[str] = []
    visible_stdout = sys.stdout
    spinner_stop = asyncio.Event()
    spinner_task: asyncio.Task[None] | None = None
    if not plain_ui and not json_metrics and sys.stdout.isatty():
        spinner_task = asyncio.create_task(
            _spinner("waseem-brain>", color_enabled=color_enabled, stop=spinner_stop)
        )

    answer_started = False
    try:
        runtime_query_context = (
            _silence_runtime_io(quiet_runtime_io)
            if isinstance(runtime, LocalRuntimeHandle)
            else contextlib.nullcontext()
        )
        with runtime_query_context:
            async for token in runtime.query(
                query_text=query_text,
                modality=modality,
                session_id=str(session_id),
            ):
                if not answer_started:
                    if spinner_task is not None:
                        spinner_stop.set()
                        await spinner_task
                        spinner_task = None
                    if not json_metrics:
                        visible_stdout.write(
                            _paint("waseem-brain> ", _BOLD, _GREEN, enabled=color_enabled)
                        )
                    answer_started = True
                response_parts.append(token)
                visible_stdout.write(token)
                visible_stdout.flush()
    finally:
        if spinner_task is not None:
            spinner_stop.set()
            await spinner_task

    if response_parts:
        visible_stdout.write("\n")
        visible_stdout.flush()

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    query_result = runtime.last_query_result() or {}
    latest_trace = query_result.get("latest_trace")
    health = query_result.get("health")
    if not isinstance(health, dict):
        health = await runtime.health()

    metrics: dict[str, Any] = {
        "elapsed_ms": round(elapsed_ms, 2),
        "response_tokens": (
            int(latest_trace["response_length_tokens"])
            if isinstance(latest_trace, dict)
            else len("".join(response_parts).split())
        ),
        "memory_node_count": health.get("memory_node_count", 0),
        "experts_loaded": health.get("experts_loaded", 0),
        "router_backend": health.get("router_backend", "unknown"),
        "vector_backend": health.get("vector_backend", "unknown"),
    }
    if isinstance(latest_trace, dict):
        metrics.update(
            {
                "expert_id": str(latest_trace["expert_id"]),
                "response_mode": latest_trace["response_mode"],
                "render_strategy": latest_trace["render_strategy"],
                "citations_count": latest_trace["citations_count"],
                "confidence": round(latest_trace["confidence"], 4),
                "outcome": latest_trace["outcome"],
                "query_coverage": round(latest_trace["query_coverage"], 4),
                "entity_match_score": round(latest_trace["entity_match_score"], 4),
                "symbol_anchor_score": round(latest_trace["symbol_anchor_score"], 4),
                "decision_trace": latest_trace["decision_trace"],
            }
        )

    if show_metrics:
        _print_metrics(metrics, json_mode=json_metrics, color_enabled=color_enabled)
    return 0


async def _interactive_chat(
    runtime: RuntimeHandleProtocol,
    *,
    settings: BrainSettings,
    session_id: SessionId,
    warm_status: dict[str, str] | None,
    show_metrics: bool,
    json_metrics: bool,
    color_enabled: bool,
    plain_ui: bool,
    quiet_runtime_io: bool,
) -> int:
    print(
        _paint(
            "Waseem Brain terminal is live. Type /status to see the full dashboard.",
            _BOLD,
            _CYAN,
            enabled=color_enabled,
        )
    )
    while True:
        try:
            prompt = input(_paint("\nwaseem@terminal> ", _BOLD, _BLUE, enabled=color_enabled)).strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nStopping Waseem Brain.")
            return 0

        if not prompt:
            continue
        if prompt in {"/quit", "/exit"}:
            return 0
        if prompt in {"/status", "/dashboard"}:
            await _print_dashboard(
                runtime,
                settings=settings,
                session_id=session_id,
                warm_status=warm_status,
                color_enabled=color_enabled,
            )
            continue
        if prompt == "/learning":
            await _print_learning_status(
                runtime,
                settings=settings,
                session_id=session_id,
                warm_status=warm_status,
                color_enabled=color_enabled,
            )
            continue
        if prompt == "/project":
            await _print_project_status(
                runtime,
                settings=settings,
                session_id=session_id,
                warm_status=warm_status,
                color_enabled=color_enabled,
            )
            continue
        if prompt == "/clear":
            _clear_screen(color_enabled=color_enabled)
            _print_banner(color_enabled=color_enabled)
            await _print_dashboard(
                runtime,
                settings=settings,
                session_id=session_id,
                warm_status=warm_status,
                color_enabled=color_enabled,
            )
            continue
        if prompt == "/health":
            print(json.dumps(await runtime.health(), indent=2))
            continue
        if prompt == "/experts":
            print(json.dumps(await runtime.experts(), indent=2))
            continue
        if prompt.startswith("/recall "):
            recall_query = prompt[len("/recall ") :].strip()
            print(json.dumps(await runtime.recall(recall_query), indent=2))
            continue
        if prompt == "/help":
            print(
                "Commands: /status, /dashboard, /learning, /project, /health, "
                "/experts, /recall <text>, /clear, /quit"
            )
            continue

        await _run_turn(
            runtime,
            query_text=prompt,
            modality="text",
            session_id=session_id,
            show_metrics=show_metrics,
            json_metrics=json_metrics,
            color_enabled=color_enabled,
            plain_ui=plain_ui,
            quiet_runtime_io=quiet_runtime_io,
        )


async def _main_async(args: argparse.Namespace) -> int:
    _enable_windows_ansi()
    color_enabled = _use_color(args.plain_ui)
    settings = load_settings()
    session_id = SessionId(args.session_id)
    runtime: RuntimeHandleProtocol
    warm_status: dict[str, str] | None = None
    daemon_available = is_runtime_daemon_running()
    if args.runtime_daemon != "never" and daemon_available:
        runtime = RuntimeDaemonClient()
        warm_status = {
            "embedding_backend": "daemon-hot",
            "text_emotion": "daemon-hot",
            "voice": "daemon-managed",
        }
    else:
        if args.runtime_daemon == "always":
            raise RuntimeError("Runtime daemon was requested but is not running")
        if not args.skip_warmup:
            warm_status = _warm_models(
                include_voice=args.include_voice_warmup,
                quiet=not args.verbose_warmup,
            )
        runtime = LocalRuntimeHandle(__import__("brain.runtime", fromlist=["LatticeBrainRuntime"]).LatticeBrainRuntime(settings=settings))
    try:
        if args.health:
            print(json.dumps(await runtime.health(), indent=2))
            return 0
        if args.experts:
            print(json.dumps(await runtime.experts(), indent=2))
            return 0
        if args.dashboard:
            if not args.plain_ui:
                _clear_screen(color_enabled=color_enabled)
                _print_banner(color_enabled=color_enabled)
            await _print_dashboard(
                runtime,
                settings=settings,
                session_id=session_id,
                warm_status=warm_status,
                color_enabled=color_enabled,
            )
            return 0

        if not args.plain_ui and not args.json_metrics:
            _clear_screen(color_enabled=color_enabled)
            _print_banner(color_enabled=color_enabled)
            await _print_dashboard(
                runtime,
                settings=settings,
                session_id=session_id,
                warm_status=warm_status,
                color_enabled=color_enabled,
            )

        if args.once:
            if not args.prompt:
                raise ValueError("A prompt or input path is required with --once")
            return await _run_turn(
                runtime,
                query_text=args.prompt,
                modality=args.modality,
                session_id=session_id,
                show_metrics=not args.no_metrics,
                json_metrics=args.json_metrics,
                color_enabled=color_enabled,
                plain_ui=args.plain_ui,
                quiet_runtime_io=not args.verbose_runtime,
            )
        if args.prompt:
            return await _run_turn(
                runtime,
                query_text=args.prompt,
                modality=args.modality,
                session_id=session_id,
                show_metrics=not args.no_metrics,
                json_metrics=args.json_metrics,
                color_enabled=color_enabled,
                plain_ui=args.plain_ui,
                quiet_runtime_io=not args.verbose_runtime,
            )
        return await _interactive_chat(
            runtime,
            settings=settings,
            session_id=session_id,
            warm_status=warm_status,
            show_metrics=not args.no_metrics,
            json_metrics=args.json_metrics,
            color_enabled=color_enabled,
            plain_ui=args.plain_ui,
            quiet_runtime_io=not args.verbose_runtime,
        )
    finally:
        await runtime.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive or one-shot CLI for Lattice Brain.")
    parser.add_argument("prompt", nargs="?", help="Prompt text, URL, or file path based on modality.")
    parser.add_argument(
        "--modality",
        choices=("text", "url", "file", "voice"),
        default="text",
        help="How to interpret the prompt argument.",
    )
    parser.add_argument(
        "--session-id",
        default=f"cli-{int(time.time())}",
        help="Stable session id for multi-turn chat and recall.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single turn and exit. If omitted and no prompt is supplied, opens interactive chat.",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Print the branded Waseem Brain dashboard and exit.",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Print runtime health and exit.",
    )
    parser.add_argument(
        "--experts",
        action="store_true",
        help="Print loaded expert status and exit.",
    )
    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Skip local model warmup before serving queries.",
    )
    parser.add_argument(
        "--include-voice-warmup",
        action="store_true",
        help="Warm the voice model too, even for text/url sessions.",
    )
    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="Do not print per-turn metrics after each response.",
    )
    parser.add_argument(
        "--json-metrics",
        action="store_true",
        help="Print per-turn metrics as JSON instead of key-value lines.",
    )
    parser.add_argument(
        "--plain-ui",
        action="store_true",
        help="Disable the branded dashboard, colors, and animated terminal UI.",
    )
    parser.add_argument(
        "--verbose-warmup",
        action="store_true",
        help="Show library output during warmup instead of silencing it.",
    )
    parser.add_argument(
        "--verbose-runtime",
        action="store_true",
        help="Reserved for future runtime-side debug logging.",
    )
    parser.add_argument(
        "--runtime-daemon",
        choices=("auto", "always", "never"),
        default="auto",
        help="Use the hot runtime daemon when available, require it, or disable it.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
