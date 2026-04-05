from __future__ import annotations

import unicodedata
from collections.abc import Callable

from ..types import NormalizedSignal, Result, err, ok
from .base import InputAdapter


class TextAdapter(InputAdapter):
    def __init__(self, language_detector: Callable[[str], str] | None = None) -> None:
        self._language_detector = language_detector

    def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]:
        if not isinstance(raw_input, str):
            return err("TextAdapter expects string input")

        text = unicodedata.normalize("NFKC", raw_input.strip())
        if not text:
            return err("Text input is empty after normalization")

        language = self._detect_language(text)
        return ok(
            {
                "text": text,
                "modality": "text",
                "metadata": {
                    "language": language,
                    "length": len(text),
                    "normalized_unicode": True,
                },
            }
        )

    def _detect_language(self, text: str) -> str:
        if self._language_detector is not None:
            return self._language_detector(text)

        try:
            from langdetect import detect  # type: ignore
        except Exception:
            alphabetic = [char for char in text if char.isalpha()]
            if not alphabetic:
                return "unknown"
            ascii_ratio = sum(char.isascii() for char in alphabetic) / len(alphabetic)
            return "en" if ascii_ratio > 0.8 else "unknown"

        try:
            return str(detect(text))
        except Exception:
            return "unknown"
