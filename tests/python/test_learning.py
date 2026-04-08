from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from brain.dialogue import DialoguePlanner
from brain.experts.assembler import ResponseAssembler
from brain.learning.features import entity_match_score, query_coverage_score
from brain.learning.policy import (
    ResponsePolicyExporter,
    ResponsePolicyTrainer,
    load_response_policy,
)
from brain.types import ExpertId, SessionId
from tests.python.support import make_settings


def _trace(
    *,
    session_id: str,
    expert_id: str,
    query: str,
    response: str,
    intent: str,
    mode: str,
    strategy: str,
    citations: int,
    confidence: float,
    outcome: str,
) -> dict[str, object]:
    has_next_step = "Next useful step:" in response
    return {
        "session_id": SessionId(session_id),
        "expert_id": ExpertId(expert_id),
        "query": query,
        "response": response,
        "dialogue_intent": intent,
        "response_mode": mode,
        "render_strategy": strategy,
        "citations_count": citations,
        "has_next_step": has_next_step,
        "query_coverage": query_coverage_score(query, response),
        "entity_match_score": entity_match_score(query, response),
        "response_length_tokens": len(response.split()),
        "confidence": confidence,
        "decision_trace": "test-trace",
        "outcome": outcome,
        "timestamp": 1.0,
    }


class ResponsePolicyLearningTestCase(unittest.TestCase):
    def test_policy_trainer_exports_and_loads_artifact(self) -> None:
        traces = [
            _trace(
                session_id="s1",
                expert_id="code-general",
                query="fix python gateway",
                response="answer one",
                intent="code",
                mode="answer",
                strategy="grounded",
                citations=1,
                confidence=0.8,
                outcome="answered",
            ),
            _trace(
                session_id="s2",
                expert_id="code-general",
                query="fix python gateway bug",
                response="plan one",
                intent="code",
                mode="plan",
                strategy="stepwise",
                citations=3,
                confidence=0.95,
                outcome="answered",
            ),
            _trace(
                session_id="s3",
                expert_id="code-general",
                query="implement router cleanup",
                response="plan two",
                intent="code",
                mode="plan",
                strategy="stepwise",
                citations=2,
                confidence=0.9,
                outcome="answered",
            ),
            _trace(
                session_id="s4",
                expert_id="language-en",
                query="fix it",
                response="what exactly should I fix?",
                intent="follow_up",
                mode="clarify",
                strategy="clarify",
                citations=0,
                confidence=0.55,
                outcome="clarification_requested",
            ),
        ]
        artifact = ResponsePolicyTrainer().fit(traces)
        self.assertEqual(artifact.preferred_mode("code"), "plan")
        self.assertEqual(artifact.preferred_strategy("code", "plan"), "stepwise")
        self.assertTrue(artifact.wants_next_step("code"))
        self.assertGreaterEqual(artifact.clarification_confidence_floor, 0.6)
        self.assertIn("plan", artifact.candidate_ranker_profiles)
        self.assertGreater(
            artifact.candidate_score_adjustment(
                "plan",
                citations_count=2,
                has_next_step=True,
                confidence=0.9,
                entity_match_score=0.0,
                query_coverage=0.8,
                symbol_anchor_score=0.8,
                response_length_tokens=12,
            ),
            artifact.candidate_score_adjustment(
                "plan",
                citations_count=0,
                has_next_step=False,
                confidence=0.4,
                entity_match_score=0.0,
                query_coverage=0.1,
                symbol_anchor_score=0.1,
                response_length_tokens=2,
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "response-policy.json"
            ResponsePolicyExporter().export_model(output_path, artifact)
            loaded = load_response_policy(output_path)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.preferred_mode("code"), "plan")
        self.assertEqual(loaded.preferred_strategy("code", "plan"), "stepwise")
        self.assertTrue(loaded.wants_next_step("code"))
        self.assertIn("plan", loaded.candidate_ranker_profiles)

    def test_dialogue_planner_uses_policy_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            policy_path = settings.expert_dir.parent / "response-policy.json"
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            ResponsePolicyExporter().export_model(
                policy_path,
                ResponsePolicyTrainer().fit(
                    [
                        _trace(
                            session_id="s1",
                            expert_id="code-general",
                            query="fix python gateway",
                            response="plan one",
                            intent="code",
                            mode="plan",
                            strategy="stepwise",
                            citations=2,
                            confidence=0.95,
                            outcome="answered",
                        ),
                        _trace(
                            session_id="s2",
                            expert_id="code-general",
                            query="router cleanup",
                            response="plan two",
                            intent="code",
                            mode="plan",
                            strategy="stepwise",
                            citations=2,
                            confidence=0.9,
                            outcome="answered",
                        ),
                        _trace(
                            session_id="s3",
                            expert_id="language-en",
                            query="fix it",
                            response="clarify",
                            intent="follow_up",
                            mode="clarify",
                            strategy="clarify",
                            citations=0,
                            confidence=0.55,
                            outcome="clarification_requested",
                        ),
                    ]
                ),
            )
            planner = DialoguePlanner(settings=settings)
            state = {
                "intent": "code",
                "style": "concise",
                "needs_clarification": False,
                "prefers_steps": False,
                "references_workspace": True,
                "references_memory": False,
                "asks_for_reasoning": False,
                "confidence": 0.8,
                "signals": [],
            }
            plan = planner.build_plan(
                {
                    "text": "fix python gateway",
                    "modality": "text",
                    "metadata": {},
                    "session_id": SessionId("plan"),
                },
                state,
                router_confidence=0.7,
                has_evidence=True,
                has_memory_answer=False,
            )
            self.assertEqual(plan["mode"], "plan")

            clarify_state = {
                "intent": "follow_up",
                "style": "concise",
                "needs_clarification": True,
                "prefers_steps": False,
                "references_workspace": False,
                "references_memory": True,
                "asks_for_reasoning": False,
                "confidence": 0.55,
                "signals": [],
            }
            clarify_plan = planner.build_plan(
                {
                    "text": "fix it",
                    "modality": "text",
                    "metadata": {},
                    "session_id": SessionId("clarify"),
                },
                clarify_state,
                router_confidence=0.6,
                has_evidence=False,
                has_memory_answer=False,
            )
            self.assertEqual(clarify_plan["mode"], "clarify")

    def test_response_assembler_uses_policy_strategy_bias(self) -> None:
        policy = ResponsePolicyTrainer().fit(
            [
                _trace(
                    session_id="s1",
                    expert_id="code-general",
                    query="fix gateway",
                    response="plan one",
                    intent="code",
                    mode="plan",
                    strategy="stepwise",
                    citations=2,
                    confidence=0.9,
                    outcome="answered",
                ),
                _trace(
                    session_id="s2",
                    expert_id="code-general",
                    query="refactor gateway",
                    response="plan two",
                    intent="code",
                    mode="plan",
                    strategy="stepwise",
                    citations=1,
                    confidence=0.8,
                    outcome="answered",
                ),
                _trace(
                    session_id="s3",
                    expert_id="language-en",
                    query="why is this failing",
                    response="answer",
                    intent="code",
                    mode="answer",
                    strategy="grounded",
                    citations=1,
                    confidence=0.7,
                    outcome="answered",
                ),
            ]
        )
        assembler = ResponseAssembler(policy=policy)
        result = assembler.assemble(
            [
                {
                    "expert_id": ExpertId("code-general"),
                    "content": "The strongest file is python_gateway.ts",
                    "confidence": 0.75,
                    "sources": ["python_gateway.ts"],
                    "latency_ms": 1.0,
                    "citations": [],
                    "render_strategy": "grounded",
                    "summary": "grounded",
                },
                {
                    "expert_id": ExpertId("language-en"),
                    "content": "Here is the grounded answer",
                    "confidence": 0.7,
                    "sources": ["python_gateway.ts"],
                    "latency_ms": 1.0,
                    "citations": [],
                    "render_strategy": "grounded",
                    "summary": "language",
                },
            ],
            query="fix gateway",
            dialogue_state={
                "intent": "code",
                "style": "concise",
                "needs_clarification": False,
                "prefers_steps": False,
                "references_workspace": True,
                "references_memory": False,
                "asks_for_reasoning": False,
                "confidence": 0.8,
                "signals": [],
            },
            response_plan={
                "mode": "plan",
                "lead_style": "concise",
                "include_sources": True,
                "include_next_step": True,
                "max_citations": 2,
                "rationale": "test",
            },
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["render_strategy"], "stepwise")

    def test_response_assembler_uses_candidate_ranker_for_grounded_answer(self) -> None:
        policy = ResponsePolicyTrainer().fit(
            [
                _trace(
                    session_id="s1",
                    expert_id="language-en",
                    query="why is gateway failing",
                    response=(
                        "Grounded answer with evidence. Next useful step: inspect "
                        "python_gateway.ts first."
                    ),
                    intent="code",
                    mode="answer",
                    strategy="grounded",
                    citations=3,
                    confidence=0.95,
                    outcome="answered",
                ),
                _trace(
                    session_id="s2",
                    expert_id="language-en",
                    query="why is router failing",
                    response=(
                        "Grounded answer with citations. Next useful step: inspect "
                        "router.rs first."
                    ),
                    intent="code",
                    mode="answer",
                    strategy="grounded",
                    citations=2,
                    confidence=0.9,
                    outcome="answered",
                ),
                _trace(
                    session_id="s3",
                    expert_id="language-en",
                    query="why is bridge failing",
                    response="Merged answer only",
                    intent="code",
                    mode="answer",
                    strategy="direct",
                    citations=0,
                    confidence=0.55,
                    outcome="unsupported",
                ),
            ]
        )
        assembler = ResponseAssembler(policy=policy)
        result = assembler.assemble(
            [
                {
                    "expert_id": ExpertId("code-general"),
                    "content": "Gateway failure points to python_gateway.ts",
                    "confidence": 0.78,
                    "sources": ["python_gateway.ts"],
                    "latency_ms": 1.0,
                    "citations": [
                        {
                            "id": "code-1",
                            "source_type": "workspace",
                            "label": "python_gateway.ts",
                            "snippet": "Gateway failure points to python_gateway.ts",
                            "uri": "workspace://python_gateway.ts",
                        }
                    ],
                    "render_strategy": "grounded",
                    "summary": "code",
                },
                {
                    "expert_id": ExpertId("language-en"),
                    "content": "Gateway failure points to python_gateway.ts because the bridge stalls.",
                    "confidence": 0.76,
                    "sources": ["coordinator_bridge.py"],
                    "latency_ms": 1.0,
                    "citations": [
                        {
                            "id": "code-2",
                            "source_type": "workspace",
                            "label": "coordinator_bridge.py",
                            "snippet": "the bridge stalls",
                            "uri": "workspace://coordinator_bridge.py",
                        }
                    ],
                    "render_strategy": "grounded",
                    "summary": "language",
                },
            ],
            query="why is gateway failing",
            dialogue_state={
                "intent": "code",
                "style": "concise",
                "needs_clarification": False,
                "prefers_steps": False,
                "references_workspace": True,
                "references_memory": False,
                "asks_for_reasoning": True,
                "confidence": 0.82,
                "signals": [],
            },
            response_plan={
                "mode": "answer",
                "lead_style": "concise",
                "include_sources": True,
                "include_next_step": True,
                "max_citations": 2,
                "rationale": "test",
            },
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["value"]["render_strategy"], "grounded")
        self.assertGreaterEqual(len(result["value"]["citations"]), 1)
        # Accept both "Next useful step:" and "Recommended next check:" formats
        self.assertTrue(
            "Next useful step:" in result["value"]["content"] or
            "Recommended next check:" in result["value"]["content"]
        )

    def test_candidate_ranker_learns_query_anchor_preference(self) -> None:
        policy = ResponsePolicyTrainer().fit(
            [
                _trace(
                    session_id="s1",
                    expert_id="code-general",
                    query="fix python_gateway.ts timeout",
                    response=(
                        "The fix belongs in python_gateway.ts. Next useful step: inspect "
                        "python_gateway.ts first."
                    ),
                    intent="code",
                    mode="answer",
                    strategy="grounded",
                    citations=2,
                    confidence=0.95,
                    outcome="answered",
                ),
                _trace(
                    session_id="s2",
                    expert_id="code-general",
                    query="fix coordinator_bridge.py timeout",
                    response=(
                        "The issue is in coordinator_bridge.py. Next useful step: inspect "
                        "coordinator_bridge.py first."
                    ),
                    intent="code",
                    mode="answer",
                    strategy="grounded",
                    citations=2,
                    confidence=0.92,
                    outcome="answered",
                ),
                _trace(
                    session_id="s3",
                    expert_id="language-en",
                    query="fix timeout",
                    response="A generic answer without file anchors.",
                    intent="code",
                    mode="answer",
                    strategy="direct",
                    citations=0,
                    confidence=0.45,
                    outcome="unsupported",
                ),
            ]
        )
        strong = policy.candidate_score_adjustment(
            "answer",
            citations_count=2,
            has_next_step=True,
            confidence=0.9,
            entity_match_score=1.0,
            query_coverage=1.0,
            symbol_anchor_score=1.0,
            response_length_tokens=11,
        )
        weak = policy.candidate_score_adjustment(
            "answer",
            citations_count=0,
            has_next_step=False,
            confidence=0.5,
            entity_match_score=0.0,
            query_coverage=0.0,
            symbol_anchor_score=0.0,
            response_length_tokens=5,
        )
        self.assertGreater(strong, weak)
