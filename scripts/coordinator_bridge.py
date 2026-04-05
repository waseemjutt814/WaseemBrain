from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.runtime import LatticeBrainRuntime
from brain.types import SessionId

_WRITE_LOCK = asyncio.Lock()


async def _write_message(message: dict[str, Any]) -> None:
    async with _WRITE_LOCK:
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()


def _decode_query_payload(payload: dict[str, Any]) -> tuple[object, str]:
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


async def _handle_request(
    runtime: LatticeBrainRuntime,
    request: dict[str, Any],
) -> bool:
    request_id = str(request.get("id", ""))
    command = str(request.get("command", "")).strip().lower()
    payload = request.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}

    if command == "shutdown":
        await _write_message({"id": request_id, "event": "response", "payload": {"ok": True}})
        return False

    try:
        if command == "health":
            await _write_message({"id": request_id, "event": "response", "payload": runtime.health()})
            return True

        if command == "recall":
            query = str(payload.get("query", ""))
            limit = int(payload.get("limit", 5))
            await _write_message(
                {
                    "id": request_id,
                    "event": "response",
                    "payload": runtime.recall(query, limit=limit),
                }
            )
            return True

        if command == "experts":
            await _write_message({"id": request_id, "event": "response", "payload": runtime.experts()})
            return True

        if command == "query":
            raw_input, modality_hint = _decode_query_payload(payload)
            session_id = SessionId(str(payload.get("session_id", "anonymous-session")))
            async for token in runtime.query(raw_input, modality_hint, session_id):
                await _write_message({"id": request_id, "event": "token", "content": token})
            try:
                runtime.flush_session_traces(session_id)
            except Exception as exc:
                sys.stderr.write(f"[bridge-learning] {exc}\n")
                sys.stderr.flush()
            await _write_message({"id": request_id, "event": "done", "content": ""})
            return True

        raise ValueError(f"Unsupported command: {command or '<missing>'}")
    except Exception as exc:
        await _write_message({"id": request_id, "event": "error", "content": str(exc)})
        return True


async def _serve() -> None:
    runtime = LatticeBrainRuntime()
    tasks: set[asyncio.Task[bool]] = set()
    try:
        while True:
            raw_line = await asyncio.to_thread(sys.stdin.readline)
            if raw_line == "":
                break
            line = raw_line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                await _write_message({"id": "", "event": "error", "content": f"Invalid JSON: {exc}"})
                continue
            if not isinstance(request, dict):
                await _write_message(
                    {
                        "id": "",
                        "event": "error",
                        "content": "Bridge requests must be JSON objects",
                    }
                )
                continue
            if str(request.get("command", "")).strip().lower() == "shutdown":
                should_continue = await _handle_request(runtime, request)
                if not should_continue:
                    break
                continue

            task = asyncio.create_task(_handle_request(runtime, request))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        runtime.close()


def main() -> None:
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
