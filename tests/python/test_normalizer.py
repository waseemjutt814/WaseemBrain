from __future__ import annotations

import io
import unittest
from unittest.mock import patch
import wave

from brain.normalizer import normalize
from brain.normalizer.document_adapter import DocumentAdapter
from brain.normalizer.text_adapter import TextAdapter
from brain.normalizer.url_adapter import UrlAdapter
from brain.normalizer.voice_adapter import VoiceAdapter
from brain.types import SessionId


def _build_wav_bytes(*, sample_rate: int = 8000, channels: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frame = b"\x10\x00" * channels
        wav_file.writeframes(frame * 32)
    return buffer.getvalue()


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
        self.assertEqual(result["value"]["metadata"]["audio_container"], "pcm16")

    def test_voice_adapter_accepts_wav_payload_and_tracks_metadata(self) -> None:
        adapter = VoiceAdapter(
            transcriber=lambda _audio: "capital of france",
            prosody_extractor=lambda _audio: {
                "pitch_mean": 1.0,
                "pitch_std": 0.1,
                "speaking_rate": 2.0,
                "amplitude_mean": 0.2,
                "onset_variance": 0.01,
            },
        )
        result = adapter.normalize(
            {
                "data": _build_wav_bytes(sample_rate=8000, channels=2),
                "mime_type": "audio/wav",
                "filename": "browser-capture.wav",
                "modality": "voice",
            }
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["metadata"]["audio_container"], "wav")
        self.assertEqual(result["value"]["metadata"]["source_sample_rate"], 8000)
        self.assertEqual(result["value"]["metadata"]["source_channels"], 2)
        self.assertEqual(result["value"]["metadata"]["normalized_sample_rate"], 16000)
        self.assertEqual(result["value"]["metadata"]["filename"], "browser-capture.wav")
        self.assertGreater(len(result["value"]["raw_audio"]), 0)

    def test_voice_adapter_rejects_unsupported_container(self) -> None:
        adapter = VoiceAdapter(
            transcriber=lambda _audio: "unused",
            prosody_extractor=lambda _audio: {
                "pitch_mean": 0.0,
                "pitch_std": 0.0,
                "speaking_rate": 0.0,
                "amplitude_mean": 0.0,
                "onset_variance": 0.0,
            },
        )
        result = adapter.normalize(
            {
                "data": b"\x1A\x45\xDF\xA3webm",
                "mime_type": "audio/webm",
                "filename": "capture.webm",
                "modality": "voice",
            }
        )
        self.assertFalse(result["ok"])
        self.assertIn("Unsupported voice container", result["error"])

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

    def test_top_level_normalize_preserves_binary_metadata(self) -> None:
        with patch.object(VoiceAdapter, "_transcribe_with_faster_whisper", return_value="hello world"):
            with patch.object(
                VoiceAdapter,
                "_extract_prosodic_features",
                return_value={
                    "pitch_mean": 0.0,
                    "pitch_std": 0.0,
                    "speaking_rate": 0.0,
                    "amplitude_mean": 0.0,
                    "onset_variance": 0.0,
                },
            ):
                result = normalize(
                    {
                        "data": _build_wav_bytes(),
                        "filename": "browser.wav",
                        "mime_type": "audio/wav",
                        "modality": "voice",
                    },
                    "voice",
                    SessionId("session-voice"),
                )
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["session_id"], SessionId("session-voice"))
        self.assertEqual(result["value"]["filename"], "browser.wav")
        self.assertEqual(result["value"]["mime_type"], "audio/wav")
        self.assertEqual(result["value"]["metadata"]["audio_container"], "wav")


if __name__ == "__main__":
    unittest.main()
