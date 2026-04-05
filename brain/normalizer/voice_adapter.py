from __future__ import annotations

import statistics
import time
from array import array
from collections.abc import Callable
from itertools import pairwise
from typing import Any, ClassVar

from ..config import BrainSettings, load_settings
from ..types import NormalizedSignal, Result, err, ok
from .base import InputAdapter


class VoiceAdapter(InputAdapter):
    _model: ClassVar[Any | None] = None
    _loaded_model_name: ClassVar[str | None] = None

    def __init__(
        self,
        settings: BrainSettings | None = None,
        transcriber: Callable[[bytes], str] | None = None,
        prosody_extractor: Callable[[bytes], dict[str, float]] | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._transcriber = transcriber or self._transcribe_with_faster_whisper
        self._prosody_extractor = prosody_extractor or self._extract_prosodic_features

    def normalize(self, raw_input: object) -> Result[NormalizedSignal, str]:
        if not isinstance(raw_input, bytes):
            return err("VoiceAdapter expects raw PCM16 bytes")
        if not raw_input:
            return err("VoiceAdapter received empty audio input")

        try:
            transcript = self._transcriber(raw_input)
        except RuntimeError as exc:
            return err(str(exc))
        except Exception as exc:
            return err(f"Voice transcription failed: {exc}")

        features = self._prosody_extractor(raw_input)
        return ok(
            {
                "text": transcript.strip() or "[empty transcript]",
                "modality": "voice",
                "raw_audio": raw_input,
                "metadata": {
                    "prosodic_features": features,
                    "transcribed_at": time.time(),
                },
            }
        )

    def _transcribe_with_faster_whisper(self, raw_audio: bytes) -> str:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Voice transcription unavailable: install faster-whisper to enable VoiceAdapter"
            ) from exc

        model = self._load_model(WhisperModel)
        segments, _info = model.transcribe(self._pcm16_to_float32(raw_audio))
        return " ".join(segment.text for segment in segments).strip()

    def _load_model(self, model_factory: type[Any]) -> Any:
        model_name = self._settings.whisper_model
        if self.__class__._model is None or self.__class__._loaded_model_name != model_name:
            self.__class__._model = model_factory(model_name, device="cpu", compute_type="int8")
            self.__class__._loaded_model_name = model_name
        return self.__class__._model

    def _pcm16_to_float32(self, raw_audio: bytes) -> Any:
        try:
            import numpy as np
        except Exception as exc:
            raise RuntimeError(
                "Voice transcription unavailable: install numpy to preprocess PCM audio"
            ) from exc
        return np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0

    def _extract_prosodic_features(self, raw_audio: bytes) -> dict[str, float]:
        samples = array("h")
        samples.frombytes(raw_audio)
        if not samples:
            return {
                "pitch_mean": 0.0,
                "pitch_std": 0.0,
                "speaking_rate": 0.0,
                "amplitude_mean": 0.0,
                "onset_variance": 0.0,
            }

        normalized = [sample / 32768.0 for sample in samples]
        amplitude_values = [abs(sample) for sample in normalized]
        amplitude_mean = sum(amplitude_values) / len(amplitude_values)

        zero_crossings = 0
        for previous, current in pairwise(normalized):
            if (previous < 0 <= current) or (previous >= 0 > current):
                zero_crossings += 1
        duration_seconds = max(len(normalized) / 16000.0, 1e-6)
        pitch_mean = zero_crossings / (2.0 * duration_seconds)

        frame_size = 400
        frames = [
            normalized[index : index + frame_size]
            for index in range(0, len(normalized), frame_size)
        ]
        frame_energies = [
            sum(abs(sample) for sample in frame) / max(len(frame), 1) for frame in frames if frame
        ]
        onset_variance = statistics.pvariance(frame_energies) if len(frame_energies) > 1 else 0.0
        speaking_rate = (
            sum(1 for value in frame_energies if value > amplitude_mean) / duration_seconds
        )

        return {
            "pitch_mean": float(pitch_mean),
            "pitch_std": float(
                statistics.pstdev(amplitude_values) if len(amplitude_values) > 1 else 0.0
            ),
            "speaking_rate": float(speaking_rate),
            "amplitude_mean": float(amplitude_mean),
            "onset_variance": float(onset_variance),
        }
