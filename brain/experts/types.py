from __future__ import annotations

from typing import Literal, TypedDict

from ..types import (
    DialogueState,
    EvidenceReference,
    ExpertId,
    MemoryNode,
    ResponsePlan,
    SessionId,
)


class ExpertArtifact(TypedDict):
    name: str
    path: str
    kind: str


class ExpertMeta(TypedDict):
    id: ExpertId
    name: str
    domains: list[str]
    kind: Literal["grounded-language", "repo-code", "geography-dataset"]
    artifact_root: str
    artifacts: list[ExpertArtifact]
    capabilities: list[str]
    load_strategy: Literal["lazy", "pinned"]
    description: str


class AssembledResponse(TypedDict):
    content: str
    confidence: float
    conflict: bool
    sources: list[str]


class ExpertRequest(TypedDict):
    query: str
    session_id: SessionId
    memory_nodes: list[MemoryNode]
    internet_citations: list[EvidenceReference]
    dialogue_state: DialogueState
    response_plan: ResponsePlan
