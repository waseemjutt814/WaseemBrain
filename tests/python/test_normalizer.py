from __future__ import annotations

import unittest
from unittest.mock import patch

from brain.normalizer import normalize
from brain.normalizer.document_adapter import DocumentAdapter
from brain.normalizer.text_adapter import TextAdapter
from brain.normalizer.url_adapter import UrlAdapter
from brain.normalizer.voice_adapter import VoiceAdapter
from brain.types import SessionId


class NormalizerTestCase(unittest.TestCase):
    def test_text_adapter_normalizes_unicode(self) -> None:
        result = TextAdapter(language_detector=lambda _text: "en").normalize("  caf  ")
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["text"], "caf")

    def test_text_adapter_rejects_empty(self) -> None:
        result = TextAdapter().normalize("   ")
        self.assertFalse(result["ok"])

    def test_voice_adapter_with_injected_dependencies(self) -> None:
        adapter = VoiceAdapter(
            transcriber=lambda _audio: "hello world",
            prosody_extractor=lambda _audio: {
                "pitch_mean": 1.0,
                "pitch_std": 0.1,
                "speaking_rate": 2.0,
                "amplitude_mean": 0.2,
                "onset_variance": 0.01,
            },
        )
        result = adapter.normalize((b"\x00\x01") * 16)
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["modality"], "voice")

    def test_document_adapter_uses_printable_fallback(self) -> None:
        payload = b"%PDF-1.4\nThis is a fake PDF payload with readable text"
        result = DocumentAdapter("sample.pdf").normalize(payload)
        self.assertTrue(result["ok"])
        self.assertIn("fake PDF payload", result["value"]["text"])

    def test_url_adapter_with_injected_fetcher(self) -> None:
        adapter = UrlAdapter(
            fetcher=lambda _url: "<html><title>Test</title><body>Hello from page</body></html>"
        )
        result = adapter.normalize("https://example.com")
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["metadata"]["title"], "Test")

    def test_top_level_normalize_routes_by_hint(self) -> None:
        with patch.object(
            UrlAdapter,
            "_fetch_html",
            return_value="<html><title>Example</title><body>Example body</body></html>",
        ):
            result = normalize("https://example.com", "url", SessionId("session-1"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["session_id"], SessionId("session-1"))
        self.assertEqual(result["value"]["modality"], "url")


if __name__ == "__main__":
    unittest.main()
