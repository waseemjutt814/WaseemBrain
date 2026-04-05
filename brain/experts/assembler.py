from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

from ..config import BrainSettings, load_settings
from ..locale import LocaleEngine
from ..learning.features import (
    entity_match_score,
    query_coverage_score,
    symbol_anchor_score,
)
from ..learning.policy import ResponsePolicyArtifact, load_response_policy
from ..types import (
    DialogueState,
    EvidenceReference,
    ExpertId,
    ExpertOutput,
    RenderStrategy,
    ResponsePlan,
    Result,
    err,
    ok,
)

_ASSEMBLER_ID = ExpertId("response-assembler")


class _ResponseCandidate(TypedDict):
    content: str
    citations: list[EvidenceReference]
    confidence: float
    has_next_step: bool
    render_strategy: RenderStrategy
    response_length_tokens: int
    sources: list[str]
    summary: str
    score: float


class ResponseAssembler:
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

    def assemble(
        self,
        outputs: list[ExpertOutput],
        *,
        query: str = "",
        dialogue_state: DialogueState | None = None,
        response_plan: ResponsePlan | None = None,
    ) -> Result[ExpertOutput, str]:
        if not outputs:
            return err("Cannot assemble an empty expert output list")
        if len(outputs) == 1:
            return ok(self._realize_single(outputs[0], query, dialogue_state, response_plan))

        ranked_outputs = sorted(outputs, key=lambda output: output["confidence"], reverse=True)
        contents = [output["content"] for output in outputs]
        overlap = self._token_overlap(contents)
        citations = self._dedupe_citations(
            [
                citation
                for output in ranked_outputs
                for citation in (output["citations"] if "citations" in output else [])
            ]
        )

        candidates: list[_ResponseCandidate] = [
            self._direct_candidate(
                ranked_outputs,
                query,
                overlap,
                dialogue_state,
                response_plan,
            ),
            self._grounded_candidate(
                ranked_outputs, query, dialogue_state, response_plan, citations
            ),
            self._stepwise_candidate(
                ranked_outputs, query, dialogue_state, response_plan, citations
            ),
        ]
        selected = max(candidates, key=lambda candidate: candidate["score"])
        return ok(
            {
                "expert_id": _ASSEMBLER_ID,
                "content": selected["content"],
                "confidence": selected["confidence"],
                "sources": selected["sources"],
                "latency_ms": sum(output["latency_ms"] for output in outputs),
                "citations": selected["citations"],
                "render_strategy": selected["render_strategy"],
                "summary": selected["summary"],
            }
        )

    def _realize_single(
        self,
        output: ExpertOutput,
        query: str,
        dialogue_state: DialogueState | None,
        response_plan: ResponsePlan | None,
    ) -> ExpertOutput:
        lead = self._lead_text(dialogue_state, response_plan, has_multiple=False)
        content = output["content"].strip()
        if lead and lead not in content:
            content = f"{lead}\n{content}"
        next_step = self._next_step_line(dialogue_state, response_plan, output["sources"])
        if next_step and next_step not in content:
            content = f"{content}\n{next_step}"
        summary = output["summary"]
        if query and summary == output["summary"]:
            summary = f"{summary} for '{query[:80]}'"
        render_strategy = output["render_strategy"] if "render_strategy" in output else "single"
        return {
            **output,
            "content": content,
            "render_strategy": render_strategy,
            "summary": summary,
        }

    def _direct_candidate(
        self,
        outputs: list[ExpertOutput],
        query: str,
        overlap: float,
        dialogue_state: DialogueState | None,
        response_plan: ResponsePlan | None,
    ) -> _ResponseCandidate:
        if overlap >= 0.35:
            content = "\n\n".join(dict.fromkeys(output["content"] for output in outputs))
        else:
            content = "\n\n".join(output["content"] for output in outputs)
        confidence = min(
            1.0,
            _mean(output["confidence"] for output in outputs) * (0.9 + (overlap * 0.1)),
        )
        citations: list[EvidenceReference] = []
        sources = sorted({source for output in outputs for source in output["sources"]})
        response_length_tokens = len(content.split())
        query_coverage = query_coverage_score(query, content)
        entity_match = entity_match_score(query, content)
        symbol_anchor = symbol_anchor_score(query, content)
        score = (
            0.45
            + overlap
            + self._policy_adjustment(
                dialogue_state,
                response_plan,
                strategy="direct",
                citations_count=len(citations),
                has_next_step=False,
                confidence=confidence,
                entity_match_score=entity_match,
                query_coverage=query_coverage,
                symbol_anchor_score=symbol_anchor,
                response_length_tokens=response_length_tokens,
            )
        )
        return {
            "content": content,
            "citations": citations,
            "confidence": confidence,
            "has_next_step": False,
            "render_strategy": "direct",
            "response_length_tokens": response_length_tokens,
            "sources": sources,
            "summary": "Direct merge of grounded outputs",
            "score": score,
        }

    def _grounded_candidate(
        self,
        outputs: list[ExpertOutput],
        query: str,
        dialogue_state: DialogueState | None,
        response_plan: ResponsePlan | None,
        citations: list[EvidenceReference],
    ) -> _ResponseCandidate:
        lead = self._lead_text(dialogue_state, response_plan, has_multiple=True)
        lines = [lead] if lead else []
        included_outputs = outputs[:2]
        included_citations: list[EvidenceReference] = []
        if query:
            lines.append(f"{LocaleEngine.t(loc, 'query_focus')} {query.strip()[:160]}")
        lines.extend(output["content"].strip() for output in included_outputs)
        if citations and response_plan is not None and response_plan["include_sources"]:
            included_citations = citations[: response_plan["max_citations"]]
            lines.append("Grounding:")
            lines.extend(
                f"- {citation['label']}: {citation['snippet']}"
                for citation in included_citations
            )
        next_step = self._next_step_line(
            dialogue_state,
            response_plan,
            [source for output in included_outputs for source in output["sources"]],
        )
        if next_step:
            lines.append(f"\n{next_step}")
        content = "\n".join(line for line in lines if line.strip())
        confidence = min(
            1.0,
            _mean(output["confidence"] for output in included_outputs)
            + (min(len(included_citations), 2) * 0.02),
        )
        response_length_tokens = len(content.split())
        query_coverage = query_coverage_score(query, content)
        entity_match = entity_match_score(query, content)
        symbol_anchor = symbol_anchor_score(query, content)
        sources = sorted({source for output in included_outputs for source in output["sources"]})
        score = 0.6 + min(len(included_citations), 3) * 0.06
        if dialogue_state is not None and dialogue_state["style"] == "supportive":
            score += 0.05
        score += self._policy_adjustment(
            dialogue_state,
            response_plan,
            strategy="grounded",
            citations_count=len(included_citations),
            has_next_step=next_step is not None,
            confidence=confidence,
            entity_match_score=entity_match,
            query_coverage=query_coverage,
            symbol_anchor_score=symbol_anchor,
            response_length_tokens=response_length_tokens,
        )
        return {
            "content": content,
            "citations": included_citations,
            "confidence": confidence,
            "has_next_step": next_step is not None,
            "render_strategy": "grounded",
            "response_length_tokens": response_length_tokens,
            "sources": sources,
            "summary": "Grounded blended response",
            "score": score,
        }

    def _stepwise_candidate(
        self,
        outputs: list[ExpertOutput],
        query: str,
        dialogue_state: DialogueState | None,
        response_plan: ResponsePlan | None,
        citations: list[EvidenceReference],
    ) -> _ResponseCandidate:
        lines = ["Here is the clearest stepwise path I can support right now:"]
        included_outputs = outputs[:1]
        included_citations = citations[:2]
        if query:
            lines.append(f"1. Anchor the task around: {query.strip()[:160]}")
        top_sources = [source for output in outputs for source in output["sources"]][:2]
        if top_sources:
            lines.append(f"2. Start from the strongest evidence: {', '.join(top_sources)}")
        lines.append("3. Use the grounded details below before making a change or conclusion.")
        lines.extend(output["content"].strip() for output in included_outputs)
        if included_citations:
            lines.append("Evidence:")
            lines.extend(
                f"- {citation['label']}: {citation['snippet']}" for citation in included_citations
            )
        next_step = self._next_step_line(
            dialogue_state,
            response_plan,
            top_sources,
        )
        if next_step:
            lines.append(f"\n{next_step}")
        content = "\n".join(lines)
        confidence = min(
            1.0,
            max(output["confidence"] for output in included_outputs)
            + (0.05 if response_plan is not None and response_plan["mode"] == "plan" else 0.0),
        )
        response_length_tokens = len(content.split())
        query_coverage = query_coverage_score(query, content)
        entity_match = entity_match_score(query, content)
        symbol_anchor = symbol_anchor_score(query, content)
        score = 0.4
        if response_plan is not None and response_plan["mode"] == "plan":
            score += 0.35
        if dialogue_state is not None and dialogue_state["prefers_steps"]:
            score += 0.15
        score += self._policy_adjustment(
            dialogue_state,
            response_plan,
            strategy="stepwise",
            citations_count=len(included_citations),
            has_next_step=next_step is not None,
            confidence=confidence,
            entity_match_score=entity_match,
            query_coverage=query_coverage,
            symbol_anchor_score=symbol_anchor,
            response_length_tokens=response_length_tokens,
        )
        return {
            "content": content,
            "citations": included_citations,
            "confidence": confidence,
            "has_next_step": next_step is not None,
            "render_strategy": "stepwise",
            "response_length_tokens": response_length_tokens,
            "sources": top_sources,
            "summary": "Stepwise grounded response",
            "score": score,
        }

    def _lead_text(
        self,
        dialogue_state: DialogueState | None,
        response_plan: ResponsePlan | None,
        *,
        has_multiple: bool,
    ) -> str:
        loc = dialogue_state.get("locale", "en") if dialogue_state else "en"
        if response_plan is not None and response_plan["mode"] == "memory-recall":
            return LocaleEngine.t(loc, "grounded_answer_lead")
        
        if not has_multiple and dialogue_state and dialogue_state["intent"] != "code":
            return ""

        key = "grounded_answer_lead"
        if response_plan and response_plan["mode"] == "plan":
            key = "grounded_plan_lead"
        elif dialogue_state and dialogue_state["intent"] == "code":
            key = "code_expert_lead"
            
        return LocaleEngine.t(loc, key)

    def _next_step_line(
        self,
        dialogue_state: DialogueState | None,
        response_plan: ResponsePlan | None,
        sources: list[str],
    ) -> str | None:
        if response_plan is None or not response_plan["include_next_step"]:
            return None
        loc = dialogue_state.get("locale", "en") if dialogue_state else "en"
        if sources:
            lead = LocaleEngine.t(loc, "code_expert_next_step")
            return f"{lead} {sources[0]}."
        return None

    def _dedupe_citations(
        self, citations: list[EvidenceReference]
    ) -> list[EvidenceReference]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[EvidenceReference] = []
        for citation in citations:
            key = (citation["source_type"], citation["label"], citation["snippet"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(citation)
        return deduped

    def _token_overlap(self, contents: list[str]) -> float:
        token_sets = [set(content.lower().split()) for content in contents if content.strip()]
        if len(token_sets) < 2:
            return 1.0
        shared = set.intersection(*token_sets)
        total = set.union(*token_sets)
        return len(shared) / max(len(total), 1)

    def _policy_adjustment(
        self,
        dialogue_state: DialogueState | None,
        response_plan: ResponsePlan | None,
        *,
        strategy: str,
        citations_count: int,
        has_next_step: bool,
        confidence: float,
        entity_match_score: float,
        query_coverage: float,
        symbol_anchor_score: float,
        response_length_tokens: int,
    ) -> float:
        strategy_bias = 0.0
        ranker_bias = 0.0
        if self._policy is None:
            return 0.0
        if dialogue_state is not None and response_plan is not None:
            preferred = self._policy.preferred_strategy(
                dialogue_state["intent"], response_plan["mode"]
            )
            if preferred is not None:
                strategy_bias = 0.2 if preferred == strategy else -0.05
        if response_plan is not None:
            ranker_bias = self._policy.candidate_score_adjustment(
                response_plan["mode"],
                citations_count=citations_count,
                has_next_step=has_next_step,
                confidence=confidence,
                entity_match_score=entity_match_score,
                query_coverage=query_coverage,
                symbol_anchor_score=symbol_anchor_score,
                response_length_tokens=response_length_tokens,
            )
        return strategy_bias + ranker_bias


def _mean(values: Iterable[float]) -> float:
    values_list = list(values)
    return sum(values_list) / max(len(values_list), 1)
