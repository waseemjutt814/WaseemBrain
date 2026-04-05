from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, Literal, TypeAlias, TypedDict, TypeGuard, TypeVar

T = TypeVar("T")
E = TypeVar("E")

EmotionName = Literal[
    "neutral",
    "calm",
    "happy",
    "joy",
    "sad",
    "sadness",
    "angry",
    "anger",
    "fear",
    "surprise",
    "disgust",
    "excited",
    "confused",
    "urgent",
]
EmotionSource = Literal["text", "voice", "both"]
Modality = Literal["text", "voice", "image", "file", "url"]
EvidenceSourceType = Literal["memory", "internet", "dataset", "workspace", "session", "user"]
DialogueIntent = Literal["greeting", "code", "factual", "planning", "follow_up", "general"]
ResponseStyle = Literal["concise", "supportive", "stepwise"]
ResponseMode = Literal["answer", "clarify", "plan", "memory-recall", "unsupported"]
RenderStrategy = Literal[
    "clarify",
    "direct",
    "grounded",
    "memory",
    "single",
    "stepwise",
    "unsupported",
]


class Branded(Generic[T]):
    primitive_name: ClassVar[str] = "value"


class _BrandedStr(str, Branded[str]):
    primitive_name: ClassVar[str] = "str"

    def __new__(cls, value: str) -> _BrandedStr:
        if not isinstance(value, str):
            raise TypeError(
                f"{cls.__name__} requires {cls.primitive_name}, got {type(value).__name__}"
            )
        return str.__new__(cls, value)


class SessionId(_BrandedStr):
    """Nominal session identifier."""


class ExpertId(_BrandedStr):
    """Nominal expert identifier."""


class MemoryNodeId(_BrandedStr):
    """Nominal memory node identifier."""


class EmbeddingVector(tuple[float, ...], Branded[tuple[float, ...]]):
    primitive_name: ClassVar[str] = "sequence[float]"

    def __new__(cls, values: Iterable[float]) -> EmbeddingVector:
        if isinstance(values, (str, bytes)):
            raise TypeError("EmbeddingVector requires an iterable of floats, not text-like input")
        try:
            normalized = tuple(float(value) for value in values)
        except TypeError as exc:
            raise TypeError("EmbeddingVector requires an iterable of floats") from exc
        return tuple.__new__(cls, normalized)


class OkResult(TypedDict, Generic[T]):
    ok: Literal[True]
    value: T


class ErrResult(TypedDict, Generic[E]):
    ok: Literal[False]
    error: E


Result: TypeAlias = OkResult[T] | ErrResult[E]


def ok(value: T) -> OkResult[T]:
    return {"ok": True, "value": value}


def err(error: E) -> ErrResult[E]:
    return {"ok": False, "error": error}


def is_ok(result: Result[T, E]) -> TypeGuard[OkResult[T]]:
    return result["ok"] is True


def is_err(result: Result[T, E]) -> TypeGuard[ErrResult[E]]:
    return result["ok"] is False


class NormalizedSignal(TypedDict, total=False):
    text: str
    modality: Modality
    raw_audio: bytes
    metadata: dict[str, Any]
    session_id: SessionId
    filename: str
    mime_type: str


class EmotionContext(TypedDict):
    primary_emotion: EmotionName
    valence: float
    arousal: float
    confidence: float
    source: EmotionSource


class RouterDecision(TypedDict):
    experts_needed: list[ExpertId]
    check_memory_first: bool
    internet_needed: bool
    confidence: float
    reasoning_trace: str


class DialogueState(TypedDict):
    intent: DialogueIntent
    style: ResponseStyle
    needs_clarification: bool
    prefers_steps: bool
    references_workspace: bool
    references_memory: bool
    asks_for_reasoning: bool
    confidence: float
    signals: list[str]
    locale: str


class ResponsePlan(TypedDict):
    mode: ResponseMode
    lead_style: ResponseStyle
    include_sources: bool
    include_next_step: bool
    max_citations: int
    rationale: str
    locale: str


class EvidenceReference(TypedDict):
    id: str
    source_type: EvidenceSourceType
    label: str
    snippet: str
    uri: str


class ProvenanceRecord(TypedDict):
    source_type: EvidenceSourceType
    source_id: str
    label: str
    uri: str
    snippet: str


class MemoryNode(TypedDict):
    id: MemoryNodeId
    content: str
    embedding: EmbeddingVector
    tags: list[str]
    source: str
    created_at: float
    last_accessed: float
    access_count: int
    confidence: float
    session_id: SessionId
    source_type: EvidenceSourceType
    provenance: list[ProvenanceRecord]


class ExpertOutput(TypedDict):
    expert_id: ExpertId
    content: str
    confidence: float
    sources: list[str]
    latency_ms: float
    citations: list[EvidenceReference]
    render_strategy: RenderStrategy
    summary: str


@dataclass(frozen=True)
class SystemConstants:
    min_query_length: int
    max_experts_active: int
    idle_timeout_sec: int
    embedding_dimensions: int
    memory_recall_limit: int


SYSTEM = SystemConstants(
    min_query_length=1,
    max_experts_active=3,
    idle_timeout_sec=30,
    embedding_dimensions=384,
    memory_recall_limit=10,
)


__all__ = [
    "SYSTEM",
    "Branded",
    "DialogueIntent",
    "DialogueState",
    "EmbeddingVector",
    "EmotionContext",
    "EmotionName",
    "EmotionSource",
    "ErrResult",
    "EvidenceReference",
    "EvidenceSourceType",
    "ExpertId",
    "ExpertOutput",
    "MemoryNode",
    "MemoryNodeId",
    "Modality",
    "NormalizedSignal",
    "OkResult",
    "ProvenanceRecord",
    "RenderStrategy",
    "ResponseMode",
    "ResponsePlan",
    "ResponseStyle",
    "Result",
    "RouterDecision",
    "SessionId",
    "SystemConstants",
    "err",
    "is_err",
    "is_ok",
    "ok",
]
