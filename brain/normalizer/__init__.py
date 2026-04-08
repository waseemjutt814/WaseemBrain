from __future__ import annotations

from collections.abc import Mapping

from ..types import NormalizedSignal, Result, SessionId, err
from .base import InputAdapter
from .document_adapter import DocumentAdapter
from .text_adapter import TextAdapter
from .url_adapter import UrlAdapter
from .voice_adapter import VoiceAdapter


def _extract_binary_metadata(raw_input: object) -> tuple[bytes | None, str, str, str]:
    if not isinstance(raw_input, Mapping):
        return (raw_input if isinstance(raw_input, bytes) else None, "", "", "")

    raw_bytes = raw_input.get("data")
    if isinstance(raw_bytes, bytearray):
        raw_bytes = bytes(raw_bytes)

    filename = str(raw_input.get("filename", "")).strip()
    mime_type = str(raw_input.get("mime_type", "")).strip()
    modality = str(raw_input.get("modality", "")).strip().lower()
    return (raw_bytes if isinstance(raw_bytes, bytes) else None, filename, mime_type, modality)


def normalize(
    raw_input: object,
    modality_hint: str | None = None,
    session_id: SessionId | None = None,
) -> Result[NormalizedSignal, str]:
    normalized_hint = (modality_hint or "").strip().lower()
    active_session_id = session_id or SessionId("anonymous-session")
    binary_bytes, filename, mime_type, payload_modality = _extract_binary_metadata(raw_input)

    adapter: InputAdapter
    if normalized_hint == "text":
        adapter = TextAdapter()
    elif normalized_hint == "url":
        adapter = UrlAdapter()
    elif normalized_hint == "voice" or payload_modality == "voice":
        adapter = VoiceAdapter()
    elif normalized_hint == "file" or payload_modality == "file":
        adapter = DocumentAdapter(filename_hint=filename or normalized_hint or "upload.bin")
    elif isinstance(raw_input, bytes) and normalized_hint:
        adapter = DocumentAdapter(filename_hint=normalized_hint)
    elif isinstance(raw_input, str) and raw_input.startswith(("http://", "https://")):
        adapter = UrlAdapter()
    elif isinstance(raw_input, bytes):
        adapter = VoiceAdapter()
    elif binary_bytes is not None:
        adapter = DocumentAdapter(filename_hint=filename or normalized_hint or "upload.bin")
    elif isinstance(raw_input, str):
        adapter = TextAdapter()
    else:
        return err(f"Unsupported input type: {type(raw_input).__name__}")

    adapter_input: object = raw_input
    if type(adapter) is DocumentAdapter and binary_bytes is not None:
        adapter_input = binary_bytes

    result = adapter.normalize(adapter_input)
    if not result["ok"]:
        return result
    signal = result["value"]
    signal["session_id"] = active_session_id
    if filename:
        signal["filename"] = filename
    if mime_type:
        signal["mime_type"] = mime_type
    return {"ok": True, "value": signal}


__all__ = [
    "DocumentAdapter",
    "InputAdapter",
    "TextAdapter",
    "UrlAdapter",
    "VoiceAdapter",
    "normalize",
]
