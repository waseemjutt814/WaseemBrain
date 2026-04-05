from __future__ import annotations

from ..types import EmotionContext, NormalizedSignal
from .fusion import EmotionFuser
from .text_encoder import TextEmotionEncoder
from .voice_encoder import VoiceEmotionEncoder


def encode_emotion(signal: NormalizedSignal) -> EmotionContext:
    text_context = TextEmotionEncoder().encode(signal)
    if signal.get("modality") != "voice":
        return text_context

    voice_context = VoiceEmotionEncoder().encode(signal)
    return EmotionFuser().fuse(text_context, voice_context)


__all__ = ["EmotionFuser", "TextEmotionEncoder", "VoiceEmotionEncoder", "encode_emotion"]
