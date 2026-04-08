from __future__ import annotations

import audioop
import io
import statistics
import time
import wave
from array import array
from collections.abc import Callable, Mapping
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
        try:
            raw_audio, audio_metadata = self._normalize_audio_input(raw_input)
        except RuntimeError as exc:
            return err(str(exc))

        if not raw_audio:
            return err("VoiceAdapter received empty audio input")

        try:
            transcript = self._transcriber(raw_audio)
        except RuntimeError as exc:
            return err(str(exc))
        except Exception as exc:
            return err(f"Voice transcription failed: {exc}")

        features = self._prosody_extractor(raw_audio)
        return ok(
            {
                "text": transcript.strip() or "[empty transcript]",
                "modality": "voice",
                "raw_audio": raw_audio,
                "metadata": {
                    **audio_metadata,
                    "prosodic_features": features,
                    "transcribed_at": time.time(),
                },
            }
        )

    def _normalize_audio_input(self, raw_input: object) -> tuple[bytes, dict[str, object]]:
        if isinstance(raw_input, bytes):
            return raw_input, {
                "audio_container": "pcm16",
                "mime_type": "audio/L16",
                "normalized_sample_rate": self._settings.voice_sample_rate,
                "normalized_channels": 1,
            }
        if not isinstance(raw_input, Mapping):
            raise RuntimeError("VoiceAdapter expects raw PCM16 bytes or a binary voice payload")

        raw_bytes = raw_input.get("data")
        if isinstance(raw_bytes, bytearray):
            raw_bytes = bytes(raw_bytes)
        if not isinstance(raw_bytes, bytes):
            raise RuntimeError("Voice payload is missing binary audio data")

        mime_type = str(raw_input.get("mime_type", "")).strip().lower()
        filename = str(raw_input.get("filename", "")).strip()
        audio_format = self._detect_audio_format(raw_bytes, mime_type, filename)

        if audio_format == "wav":
            decoded_audio, decoded_metadata = self._decode_wav_to_pcm16(raw_bytes)
            decoded_metadata["mime_type"] = mime_type or "audio/wav"
            decoded_metadata["filename"] = filename
            return decoded_audio, decoded_metadata
        if audio_format == "pcm16":
            return raw_bytes, {
                "audio_container": "pcm16",
                "mime_type": mime_type or "audio/L16",
                "filename": filename,
                "normalized_sample_rate": self._settings.voice_sample_rate,
                "normalized_channels": 1,
            }
        raise RuntimeError(
            "Unsupported voice container: only raw PCM16 and uncompressed WAV audio are supported"
        )

    def _detect_audio_format(self, raw_audio: bytes, mime_type: str, filename: str) -> str:
        lowered_name = filename.lower()
        if raw_audio[:4] == b"RIFF" and raw_audio[8:12] == b"WAVE":
            return "wav"
        if raw_audio[:4] == b"OggS" or raw_audio[:4] == b"fLaC" or raw_audio[:4] == b"FORM":
            return "unsupported"
        if raw_audio[:4] == b"\x1A\x45\xDF\xA3":
            return "unsupported"
        if mime_type in {"audio/wav", "audio/wave", "audio/x-wav"} or lowered_name.endswith(".wav"):
            return "wav"
        if mime_type in {
            "",
            "application/octet-stream",
            "audio/l16",
            "audio/raw",
            "audio/pcm",
            "audio/x-pcm",
        } or lowered_name.endswith((".pcm", ".raw")):
            return "pcm16"
        if mime_type.startswith("audio/") or lowered_name.endswith((".webm", ".ogg", ".mp3", ".m4a", ".aac", ".flac")):
            return "unsupported"
        return "pcm16"

    def _decode_wav_to_pcm16(self, raw_audio: bytes) -> tuple[bytes, dict[str, object]]:
        try:
            with wave.open(io.BytesIO(raw_audio), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_rate = wav_file.getframerate()
                sample_width = wav_file.getsampwidth()
                compression = wav_file.getcomptype()
                frames = wav_file.readframes(wav_file.getnframes())
        except (wave.Error, EOFError) as exc:
            raise RuntimeError(f"Voice WAV decoding failed: {exc}") from exc

        if compression != "NONE":
            raise RuntimeError("Voice WAV decoding failed: only PCM WAV audio is supported")
        if sample_width not in {1, 2, 4}:
            raise RuntimeError("Voice WAV decoding failed: unsupported WAV sample width")

        pcm_frames = frames
        if sample_width == 1:
            pcm_frames = audioop.bias(pcm_frames, 1, -128)
        if sample_width != 2:
            pcm_frames = audioop.lin2lin(pcm_frames, sample_width, 2)
        if channels > 1:
            pcm_frames = audioop.tomono(pcm_frames, 2, 0.5, 0.5)
        if sample_rate != self._settings.voice_sample_rate:
            pcm_frames, _state = audioop.ratecv(
                pcm_frames,
                2,
                1,
                sample_rate,
                self._settings.voice_sample_rate,
                None,
            )

        return pcm_frames, {
            "audio_container": "wav",
            "source_sample_rate": sample_rate,
            "source_channels": channels,
            "source_sample_width": sample_width,
            "normalized_sample_rate": self._settings.voice_sample_rate,
            "normalized_channels": 1,
        }

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
        duration_seconds = max(len(normalized) / float(self._settings.voice_sample_rate), 1e-6)
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
