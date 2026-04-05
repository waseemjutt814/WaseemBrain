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

_QUERY_LOCK = asyncio.Lock()


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


async def _write_message(
    writer: asyncio.StreamWriter,
    message: dict[str, Any],
) -> None:
    writer.write((json.dumps(message) + "\n").encode("utf-8"))
    await writer.drain()


async def _handle_request(
    runtime: LatticeBrainRuntime,
    request: dict[str, Any],
    writer: asyncio.StreamWriter,
    shutdown_event: asyncio.Event,
) -> None:
    request_id = str(request.get("id", ""))
    command = str(request.get("command", "")).strip().lower()
    payload = request.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}

    try:
        if command == "health":
            await _write_message(
                writer,
                {"id": request_id, "event": "response", "payload": runtime.health()},
            )
            return

        if command == "recall":
            query = str(payload.get("query", ""))
            limit = int(payload.get("limit", 5))
            await _write_message(
                writer,
                {
                    "id": request_id,
                    "event": "response",
                    "payload": runtime.recall(query, limit=limit),
                }
            )
            return

        if command == "experts":
            await _write_message(
                writer,
                {"id": request_id, "event": "response", "payload": runtime.experts()},
            )
            return

        if command == "query":
            raw_input, modality_hint = _decode_query_payload(payload)
            session_id = SessionId(str(payload.get("session_id", "runtime-daemon-session")))
            async with _QUERY_LOCK:
                async for token in runtime.query(raw_input, modality_hint, session_id):
                    await _write_message(
                        writer,
                        {"id": request_id, "event": "token", "content": token},
                    )
                traces = runtime.flush_session_traces(session_id)
                latest_trace = traces[-1] if traces else None
                await _write_message(
                    writer,
                    {
                        "id": request_id,
                        "event": "done",
                        "content": "",
                        "payload": {
                            "latest_trace": latest_trace,
                            "health": runtime.health(),
                        },
                    }
                )
            return

        if command == "shutdown":
            await _write_message(
                writer,
                {"id": request_id, "event": "response", "payload": {"ok": True}},
            )
            shutdown_event.set()
            return

        raise ValueError(f"Unsupported command: {command or '<missing>'}")
    except Exception as exc:
        await _write_message(
            writer,
            {"id": request_id, "event": "error", "content": str(exc)},
        )


async def _serve(host: str, port: int) -> None:
    runtime = LatticeBrainRuntime()
    shutdown_event = asyncio.Event()

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if line == b"":
                    break
                raw = line.decode("utf-8").strip()
                if not raw:
                    continue
                try:
                    request = json.loads(raw)
                except json.JSONDecodeError as exc:
                    await _write_message(
                        writer,
                        {"id": "", "event": "error", "content": f"Invalid JSON: {exc}"},
                    )
                    continue
                if not isinstance(request, dict):
                    await _write_message(
                        writer,
                        {
                            "id": "",
                            "event": "error",
                            "content": "Runtime daemon requests must be JSON objects",
                        },
                    )
                    continue
                await _handle_request(runtime, request, writer, shutdown_event)
                if shutdown_event.is_set():
                    break
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle_client, host=host, port=port)
    try:
        async with server:
            await shutdown_event.wait()
    finally:
        server.close()
        await server.wait_closed()
        runtime.close()


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 55881
    asyncio.run(_serve(host, port))


if __name__ == "__main__":
    main()
