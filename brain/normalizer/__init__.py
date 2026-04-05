from __future__ import annotations

from ..types import NormalizedSignal, Result, SessionId, err
from .base import InputAdapter
from .document_adapter import DocumentAdapter
from .text_adapter import TextAdapter
from .url_adapter import UrlAdapter
from .voice_adapter import VoiceAdapter


def normalize(
    raw_input: object,
    modality_hint: str | None = None,
    session_id: SessionId | None = None,
) -> Result[NormalizedSignal, str]:
    normalized_hint = (modality_hint or "").strip().lower()
    active_session_id = session_id or SessionId("anonymous-session")

    adapter: InputAdapter
    if normalized_hint == "text":
        adapter = TextAdapter()
    elif normalized_hint == "url":
        adapter = UrlAdapter()
    elif normalized_hint == "voice":
        adapter = VoiceAdapter()
    elif isinstance(raw_input, bytes) and normalized_hint:
        adapter = DocumentAdapter(filename_hint=normalized_hint)
    elif isinstance(raw_input, str) and raw_input.startswith(("http://", "https://")):
        adapter = UrlAdapter()
    elif isinstance(raw_input, bytes):
        adapter = VoiceAdapter()
    elif isinstance(raw_input, str):
        adapter = TextAdapter()
    else:
        return err(f"Unsupported input type: {type(raw_input).__name__}")

    result = adapter.normalize(raw_input)
    if not result["ok"]:
        return result
    signal = result["value"]
    signal["session_id"] = active_session_id
    return {"ok": True, "value": signal}


__all__ = [
    "DocumentAdapter",
    "InputAdapter",
    "TextAdapter",
    "UrlAdapter",
    "VoiceAdapter",
    "normalize",
]
