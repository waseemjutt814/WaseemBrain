from __future__ import annotations

import re

from .locale import LocaleEngine
from .config import BrainSettings, load_settings
from .learning.policy import ResponsePolicyArtifact, load_response_policy
from .types import (
    DialogueIntent,
    DialogueState,
    EmotionContext,
    MemoryNode,
    NormalizedSignal,
    ResponsePlan,
    ResponseStyle,
)

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_./-]{2,}")
_CODE_HINTS = {
    "bug",
    "code",
    "error",
    "exception",
    "file",
    "function",
    "class",
    "stack",
    "traceback",
    "test",
    "refactor",
    "implement",
    "fix",
    "repo",
    "module",
    "python",
    "typescript",
    "rust",
    "ts",
    "py",
    "rs",
}
_PLAN_HINTS = {"plan", "steps", "roadmap", "approach", "breakdown", "strategy"}
_REASONING_HINTS = {"why", "how", "logic", "reason", "explain", "because"}
_GREETING_HINTS = {"hi", "hello", "hey", "salam", "bro", "jani"}
_FOLLOW_UP_HINTS = {"it", "that", "this", "same", "again", "continue", "also", "more"}
_AMBIGUOUS_QUERIES = {"fix it", "do it", "check it", "continue", "again", "same issue"}


class DialoguePlanner:
    def __init__(
        self,
        settings: BrainSettings | None = None,
        policy: ResponsePolicyArtifact | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        policy_path = self._settings.expert_dir.parent / "response-policy.json"
        self._policy = policy or load_response_policy(policy_path)

    def reload_policy(self) -> None:
        policy_path = self._settings.expert_dir.parent / "response-policy.json"
        self._policy = load_response_policy(policy_path)

    def build_state(
        self,
        signal: NormalizedSignal,
        emotion: EmotionContext,
        memory_nodes: list[MemoryNode],
    ) -> DialogueState:
        text = signal.get("text", "").strip()
        tokens = _tokenize(text)
        lowered = text.lower()
        signals: list[str] = []

        references_workspace = bool(set(tokens) & _CODE_HINTS) or signal.get("filename") is not None
        references_memory = bool(memory_nodes) or bool(set(tokens) & _FOLLOW_UP_HINTS)
        prefers_steps = bool(set(tokens) & _PLAN_HINTS) or lowered.startswith("how ")
        asks_for_reasoning = bool(set(tokens) & _REASONING_HINTS)

        intent: DialogueIntent = "general"
        if tokens and tokens[0] in _GREETING_HINTS and len(tokens) <= 4:
            intent = "greeting"
            signals.append("greeting")
        elif prefers_steps:
            intent = "planning"
            signals.append("planning")
        elif references_workspace:
            intent = "code"
            signals.append("workspace")
        elif any(token in {"what", "where", "who", "when"} for token in tokens[:2]):
            intent = "factual"
            signals.append("factual")
        elif references_memory:
            intent = "follow_up"
            signals.append("follow-up")

        needs_clarification = self._needs_clarification(
            lowered,
            tokens,
            references_workspace=references_workspace,
            references_memory=references_memory,
        )
        if needs_clarification:
            signals.append("clarify")

        style: ResponseStyle = "concise"
        if emotion["primary_emotion"] in {"confused", "sad", "fear", "urgent"}:
            style = "supportive"
            signals.append("supportive-tone")
        if prefers_steps:
            style = "stepwise"
            signals.append("stepwise")
        if self._policy is not None and self._policy.prefers_supportive(intent):
            style = "supportive"
            signals.append("policy-supportive")

        confidence = 0.45
        if intent in {"code", "factual", "planning"}:
            confidence += 0.2
        if references_memory:
            confidence += 0.1
        if asks_for_reasoning:
            confidence += 0.05
        if needs_clarification:
            # Drop confidence heavily so it falls below the clarification floor (usually 0.45-0.55),
            # even if it gained boosts from code/memory keywords.
            confidence -= 0.40
        confidence = max(0.1, min(0.98, confidence))
        locale = LocaleEngine.detect_locale(text)

        return {
            "intent": intent,
            "style": style,
            "needs_clarification": needs_clarification,
            "prefers_steps": prefers_steps,
            "references_workspace": references_workspace,
            "references_memory": references_memory,
            "asks_for_reasoning": asks_for_reasoning,
            "confidence": confidence,
            "signals": signals,
            "locale": locale,
        }

    def build_plan(
        self,
        signal: NormalizedSignal,
        state: DialogueState,
        *,
        router_confidence: float,
        has_evidence: bool,
        has_memory_answer: bool,
    ) -> ResponsePlan:
        del signal
        clarification_floor = (
            self._policy.clarification_confidence_floor if self._policy is not None else 0.55
        )
        # 1. Base clarification rules: must need clarification and have low confidence
        if state.get("needs_clarification", False) and state.get("confidence", 1.0) <= clarification_floor:
            # 2. Never clarify if we already hold a grounded memory answer
            if not has_memory_answer:
                # 3. Only skip clarification if the router is extremely confident AND we have evidence
                if not (router_confidence >= 0.95 and has_evidence):
                    return {
                        "mode": "clarify",
                        "lead_style": state["style"],
                        "include_sources": False,
                        "include_next_step": False,
                        "max_citations": 0,
                        "rationale": "query is too ambiguous for a grounded answer",
                        "locale": state.get("locale", "en"),
                    }
        preferred_mode = self._policy.preferred_mode(state["intent"]) if self._policy else None
        include_next_step = state["intent"] in {"code", "follow_up"}
        if self._policy is not None and self._policy.wants_next_step(state["intent"]):
            include_next_step = True
        if state["prefers_steps"] or state["intent"] == "planning":
            return {
                "mode": "plan",
                "lead_style": state["style"],
                "include_sources": has_evidence,
                "include_next_step": True,
                "max_citations": 3,
                "rationale": "user asked for an approach or stepwise breakdown",
                "locale": state.get("locale", "en"),
            }
        if (
            preferred_mode == "plan"
            and has_evidence
            and state["intent"] in {"code", "planning", "follow_up"}
        ):
            return {
                "mode": "plan",
                "lead_style": state["style"],
                "include_sources": True,
                "include_next_step": True,
                "max_citations": 3,
                "rationale": "offline response policy prefers a stepwise answer here",
                "locale": state.get("locale", "en"),
            }
        if has_memory_answer:
            return {
                "mode": "memory-recall",
                "lead_style": state["style"],
                "include_sources": True,
                "include_next_step": include_next_step,
                "max_citations": 2,
                "rationale": "high-confidence recalled session memory is available",
                "locale": state.get("locale", "en"),
            }
        return {
            "mode": "answer",
            "lead_style": state["style"],
            "include_sources": has_evidence,
            "include_next_step": include_next_step,
            "max_citations": 3 if state["references_workspace"] else 2,
            "rationale": "grounded answer path",
            "locale": state.get("locale", "en"),
        }

    def clarification_prompt(self, signal: NormalizedSignal, state: DialogueState) -> str:
        query = signal.get("text", "").strip()
        loc = state.get("locale", "en")
        if state["references_workspace"]:
            return LocaleEngine.t(loc, "clarification_prompt", query=query)
        if state["references_memory"]:
            if loc == "ur":
                return "Main continue kar sakta hon, lekin pehlay batayen ap kis puranay jawab ya file ki bat kar rahay hain?"
            return (
                "I can continue, but I need to know what 'it' refers to here. "
                "Point me to the feature, file, or earlier answer you want me to continue from."
            )
        if state["intent"] == "planning":
            if loc == "ur":
                return "Target outcome batayen aur main steps likh dunga."
            return "Tell me the target outcome or repo area and I will break it down step by step."
        if loc == "ur":
            return "Koi specific task, file, ya example batayen ta k main isko exactly verify kar sakon."
        return "Tell me the specific task, file, or example you want so I can answer it cleanly."

    def next_step_hint(self, state: DialogueState) -> str | None:
        loc = state.get("locale", "en")
        if state["intent"] == "code":
            if loc == "ur":
                return "Hum is code block pe changes design kar saktay hain."
            return (
                "I can turn this into a concrete edit plan or inspect "
                "the strongest matching file next."
            )
        if state["intent"] == "planning":
            if loc == "ur":
                return "Isko properly implement karna shuru karte hain."
            return "I can expand this into an implementation order next."
        if state["intent"] == "follow_up":
            if loc == "ur":
                return "Aap bataein aur us ke baad kya karna chahiye."
            return "I can keep going from this point once you point me at the exact part you want."
        return None

    def _needs_clarification(
        self,
        lowered: str,
        tokens: list[str],
        *,
        references_workspace: bool,
        references_memory: bool,
    ) -> bool:
        if not tokens:
            return True
        if lowered in _AMBIGUOUS_QUERIES:
            return True
        if len(tokens) <= 2 and tokens[0] not in _GREETING_HINTS and not references_memory:
            return True
        if references_workspace and len(tokens) <= 3 and not any(
            token in _CODE_HINTS for token in tokens
        ):
            return True
        if references_memory and len(tokens) <= 3 and set(tokens) <= _FOLLOW_UP_HINTS:
            return True
        return False


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())
