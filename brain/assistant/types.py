from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from ..types import EvidenceReference

AssistantRoute = Literal[
    "general_chat",
    "coding",
    "repo_work",
    "grounded_answer",
    "web_lookup",
    "system_action",
]
ProviderMode = Literal["local_grounded", "openai_compatible"]
AssistantSurface = Literal["web", "terminal", "api", "runtime"]
ActionRisk = Literal["low", "medium", "high"]
ActionInputKind = Literal["text", "number", "choice"]


class ProviderStatus(TypedDict):
    configured: bool
    mode: ProviderMode
    model: str
    reachable: bool


class RealtimeVoiceStatus(TypedDict):
    supported: bool
    mode: str


class AutomationStatus(TypedDict):
    approval_required: bool
    audit_enabled: bool


class ActionInputSpec(TypedDict):
    id: str
    label: str
    kind: ActionInputKind
    required: bool
    placeholder: str
    options: NotRequired[list[str]]


class ActionDescriptor(TypedDict):
    id: str
    label: str
    description: str
    risk: ActionRisk
    read_only: bool
    category: str
    required_inputs: list[ActionInputSpec]
    confirmation_required: bool


class ActionGroup(TypedDict):
    id: str
    label: str
    actions: list[ActionDescriptor]


class ActionPreview(TypedDict):
    action_id: str
    summary: str
    command_preview: str
    risk: ActionRisk
    inputs: dict[str, str]


class AssistantMetadata(TypedDict):
    route: AssistantRoute
    provider: ProviderStatus
    tools: list[str]
    citations_count: int
    render_strategy: str
    transcript: str
    local_mode: bool


class AssistantRequest(TypedDict, total=False):
    type: str
    session_id: str
    modality: str
    input: str
    input_base64: str
    filename: str
    mime_type: str
    action_id: str
    inputs: dict[str, str]
    confirmed: bool
    surface: AssistantSurface
    raw_input: object


class AssistantServerEvent(TypedDict, total=False):
    type: str
    content: str
    tool: str
    route: AssistantRoute
    citations: list[EvidenceReference]
    descriptor: ActionDescriptor
    preview: ActionPreview
    metadata: AssistantMetadata
