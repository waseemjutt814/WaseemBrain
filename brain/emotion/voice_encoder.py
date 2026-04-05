from __future__ import annotations

from ..types import EmotionContext, EmotionName, NormalizedSignal


class VoiceEmotionEncoder:
    def encode(self, signal: NormalizedSignal) -> EmotionContext:
        features = signal.get("metadata", {}).get("prosodic_features")
        if not isinstance(features, dict):
            return {
                "primary_emotion": "neutral",
                "valence": 0.0,
                "arousal": 0.0,
                "confidence": 0.0,
                "source": "voice",
            }

        pitch_std = float(features.get("pitch_std", 0.0))
        pitch_mean = float(features.get("pitch_mean", 0.0))
        speaking_rate = float(features.get("speaking_rate", 0.0))
        amplitude = float(features.get("amplitude_mean", 0.0))
        onset_variance = float(features.get("onset_variance", 0.0))

        primary: EmotionName = "calm"
        valence = 0.1
        if speaking_rate > 4.0 and amplitude > 0.2:
            primary = "urgent"
            valence = -0.1
        elif pitch_std > 0.35 and amplitude > 0.25:
            primary = "angry"
            valence = -0.7
        elif pitch_mean < 120.0 and amplitude < 0.1:
            primary = "sad"
            valence = -0.6
        elif onset_variance > 0.005:
            primary = "confused"
            valence = -0.2
        elif pitch_std > 0.2 and amplitude > 0.15:
            primary = "excited"
            valence = 0.5

        arousal = max(0.0, min(1.0, amplitude * 2.5 + speaking_rate / 8.0))
        confidence = max(0.1, min(0.95, 0.35 + abs(valence) * 0.4 + arousal * 0.2))
        return {
            "primary_emotion": primary,
            "valence": valence,
            "arousal": arousal,
            "confidence": confidence,
            "source": "voice",
        }
