from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from brain.types import SessionId

if TYPE_CHECKING:
    from brain.runtime import WaseemBrainRuntime

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "tmp" / "runtime-daemon"
STATE_PATH = STATE_DIR / "state.json"
LOG_PATH = STATE_DIR / "runtime-daemon.log"
DEFAULT_HOST = os.environ.get("RUNTIME_DAEMON_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("RUNTIME_DAEMON_PORT", "55881"))


def load_runtime_daemon_state() -> dict[str, Any] | None:
    if not STATE_PATH.exists():
        return None
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def is_runtime_daemon_running() -> bool:
    state = load_runtime_daemon_state()
    if state is None:
        return False
    pid = int(state.get("pid", 0))
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def build_query_payload(modality: str, raw_value: str, session_id: str) -> dict[str, object]:
    normalized = modality.strip().lower()
    if normalized == "text":
        return {"modality": "text", "input": raw_value, "session_id": session_id}
    if normalized == "url":
        return {"modality": "url", "url": raw_value, "session_id": session_id}
    path = Path(raw_value).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    raw_bytes = path.read_bytes()
    if normalized == "voice":
        return {
            "modality": "voice",
            "input_base64": base64.b64encode(raw_bytes).decode("utf-8"),
            "filename": path.name,
            "mime_type": "application/octet-stream",
            "session_id": session_id,
        }
    return {
        "modality": "file",
        "input_base64": base64.b64encode(raw_bytes).decode("utf-8"),
        "filename": path.name,
        "mime_type": "application/octet-stream",
        "session_id": session_id,
    }


class RuntimeHandleProtocol(Protocol):
    async def query(
        self,
        *,
        query_text: str,
        modality: str,
        session_id: str,
    ) -> AsyncIterator[str]: ...

    async def assistant(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]: ...

    async def health(self) -> dict[str, Any]: ...

    async def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...

    async def experts(self) -> dict[str, Any]: ...

    async def actions(self) -> dict[str, Any]: ...

    def last_query_result(self) -> dict[str, Any] | None: ...

    async def aclose(self) -> None: ...


class LocalRuntimeHandle:
    def __init__(self, runtime: "WaseemBrainRuntime") -> None:
        self._runtime = runtime
        self._last_query_result: dict[str, Any] | None = None

    async def query(
        self,
        *,
        query_text: str,
        modality: str,
        session_id: str,
    ) -> AsyncIterator[str]:
        payload = build_query_payload(modality, query_text, session_id)
        raw_input, modality_hint = _decode_payload_for_runtime(payload)
        async for token in self._runtime.query(raw_input, modality_hint, SessionId(session_id)):
            yield token
        traces = self._runtime.flush_session_traces(SessionId(session_id))
        latest_trace = traces[-1] if traces else None
        self._last_query_result = {
            "latest_trace": latest_trace,
            "health": self._runtime.health(),
        }

    async def assistant(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        session_id = SessionId(str(request.get("session_id", "assistant-session")))
        try:
            async for event in self._runtime.assistant(request):
                yield event
        finally:
            if _should_flush_assistant_request(request):
                self._runtime.flush_session_traces(session_id)

    async def health(self) -> dict[str, Any]:
        return self._runtime.health()

    async def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self._runtime.recall(query, limit=limit)

    async def experts(self) -> dict[str, Any]:
        return self._runtime.experts()

    async def actions(self) -> dict[str, Any]:
        return self._runtime.actions()

    def last_query_result(self) -> dict[str, Any] | None:
        return self._last_query_result

    async def aclose(self) -> None:
        self._runtime.close()


class RuntimeDaemonClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout_sec: float = 120.0,
    ) -> None:
        state = load_runtime_daemon_state() or {}
        self._host = host or str(state.get("host", DEFAULT_HOST))
        self._port = port or int(state.get("port", DEFAULT_PORT))
        self._timeout_sec = timeout_sec
        self._last_query_result: dict[str, Any] | None = None
        self._next_request_id = 0

    async def query(
        self,
        *,
        query_text: str,
        modality: str,
        session_id: str,
    ) -> AsyncIterator[str]:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self._host, self._port),
            timeout=self._timeout_sec,
        )
        request_id = self._build_request_id()
        payload = build_query_payload(modality, query_text, session_id)
        writer.write(
            (json.dumps({"id": request_id, "command": "query", "payload": payload}) + "\n").encode(
                "utf-8"
            )
        )
        await writer.drain()
        self._last_query_result = None
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=self._timeout_sec)
                if line == b"":
                    break
                message = json.loads(line.decode("utf-8"))
                if str(message.get("id", "")) != request_id:
                    continue
                event = str(message.get("event", ""))
                if event == "token":
                    yield str(message.get("content", ""))
                    continue
                if event == "done":
                    payload = message.get("payload", {})
                    self._last_query_result = payload if isinstance(payload, dict) else {}
                    break
                if event == "error":
                    raise RuntimeError(str(message.get("content", "Unknown runtime daemon error")))
        finally:
            writer.close()
            await writer.wait_closed()

    async def assistant(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self._host, self._port),
            timeout=self._timeout_sec,
        )
        request_id = self._build_request_id()
        writer.write(
            (json.dumps({"id": request_id, "command": "assistant", "payload": request}) + "\n").encode(
                "utf-8"
            )
        )
        await writer.drain()
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=self._timeout_sec)
                if line == b"":
                    break
                message = json.loads(line.decode("utf-8"))
                if str(message.get("id", "")) != request_id:
                    continue
                event = str(message.get("event", ""))
                if event == "assistant":
                    payload = message.get("payload", {})
                    yield payload if isinstance(payload, dict) else {}
                    continue
                if event == "done":
                    break
                if event == "error":
                    raise RuntimeError(str(message.get("content", "Unknown runtime daemon error")))
        finally:
            writer.close()
            await writer.wait_closed()

    async def health(self) -> dict[str, Any]:
        return await self._unary("health", {})

    async def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        payload = await self._unary("recall", {"query": query, "limit": limit})
        return payload if isinstance(payload, list) else []

    async def experts(self) -> dict[str, Any]:
        payload = await self._unary("experts", {})
        return payload if isinstance(payload, dict) else {}

    async def actions(self) -> dict[str, Any]:
        payload = await self._unary("actions", {})
        return payload if isinstance(payload, dict) else {"groups": []}

    def last_query_result(self) -> dict[str, Any] | None:
        return self._last_query_result

    async def aclose(self) -> None:
        return

    async def _unary(self, command: str, payload: dict[str, object]) -> Any:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self._host, self._port),
            timeout=self._timeout_sec,
        )
        request_id = self._build_request_id()
        writer.write(
            (json.dumps({"id": request_id, "command": command, "payload": payload}) + "\n").encode(
                "utf-8"
            )
        )
        await writer.drain()
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=self._timeout_sec)
                if line == b"":
                    raise RuntimeError("Runtime daemon closed the connection unexpectedly")
                message = json.loads(line.decode("utf-8"))
                if str(message.get("id", "")) != request_id:
                    continue
                event = str(message.get("event", ""))
                if event == "response":
                    return message.get("payload")
                if event == "error":
                    raise RuntimeError(str(message.get("content", "Unknown runtime daemon error")))
        finally:
            writer.close()
            await writer.wait_closed()

    def _build_request_id(self) -> str:
        self._next_request_id += 1
        return f"runtime-{self._next_request_id}"



def _should_flush_assistant_request(request: dict[str, Any]) -> bool:
    request_type = str(request.get("type", "chat.submit")).strip().lower()
    return request_type in {"chat.submit", "voice.stop", "voice.submit"}

def _decode_payload_for_runtime(payload: dict[str, object]) -> tuple[object, str]:
    modality = str(payload.get("modality", "text")).strip().lower()
    if modality == "text":
        return str(payload.get("input", "")), "text"
    if modality == "url":
        return str(payload.get("url", "")), "url"
    if modality in {"voice", "file"}:
        raw_base64 = str(payload.get("input_base64", ""))
        raw_bytes = base64.b64decode(raw_base64.encode("utf-8"))
        filename = str(payload.get("filename", modality))
        return raw_bytes, "voice" if modality == "voice" else filename
    raise ValueError(f"Unsupported query modality: {modality}")
