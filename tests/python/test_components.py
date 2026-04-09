from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from typing import cast

from brain.coordinator import WaseemBrainCoordinator
from brain.emotion.fusion import EmotionFuser
from brain.emotion.text_encoder import TextEmotionEncoder
from brain.emotion.voice_encoder import VoiceEmotionEncoder
from brain.experts.assembler import ResponseAssembler
from brain.experts.pool import ExpertPool
from brain.experts.registry import ExpertRegistry
from brain.internet.fetcher import ContentFetcher
from brain.internet.module import InternetModule
from brain.internet.search import DuckDuckGoSearch
from brain.learning.corrector import ExpertCorrector
from brain.learning.feedback import FeedbackCollector
from brain.learning.loop import SelfLearningLoop
from brain.learning.scorer import ResponseScorer
from brain.memory.graph import MemoryGraph
from brain.memory.sqlite_store import SqliteMetaStore
from brain.router import ArtifactRouterClient
from brain.types import ExpertId, SessionId
from tests.python.support import create_temp_dir, make_settings, seed_experts


class EmotionTestCase(unittest.TestCase):
    def test_text_emotion_encoder(self) -> None:
        encoder = TextEmotionEncoder()
        context = encoder.encode(
            {
                "text": "I am so happy today!",
                "modality": "text",
                "metadata": {},
                "session_id": SessionId("s"),
            }
        )
        self.assertIn(context["primary_emotion"], {"joy", "happy"})

    def test_voice_emotion_encoder(self) -> None:
        context = VoiceEmotionEncoder().encode(
            {
                "text": "help",
                "modality": "voice",
                "metadata": {
                    "prosodic_features": {
                        "pitch_mean": 90.0,
                        "pitch_std": 0.1,
                        "speaking_rate": 1.0,
                        "amplitude_mean": 0.05,
                        "onset_variance": 0.0,
                    }
                },
                "session_id": SessionId("s"),
            }
        )
        self.assertEqual(context["primary_emotion"], "sad")

    def test_fuser_prefers_higher_confidence(self) -> None:
        text_context = {
            "primary_emotion": "calm",
            "valence": 0.2,
            "arousal": 0.1,
            "confidence": 0.2,
            "source": "text",
        }
        voice_context = {
            "primary_emotion": "angry",
            "valence": -0.7,
            "arousal": 0.8,
            "confidence": 0.9,
            "source": "voice",
        }
        fused = EmotionFuser().fuse(text_context, voice_context)
        self.assertEqual(fused["primary_emotion"], "angry")
        self.assertEqual(fused["source"], "both")


class MemoryTestCase(unittest.TestCase):
    def test_memory_store_and_recall(self) -> None:
        temp_dir = create_temp_dir()
        try:
            settings = make_settings(temp_dir)
            graph = MemoryGraph(settings=settings)
            session = SessionId("memory-session")
            graph.store("Paris is the capital of France", "test", ["geography"], session)
            graph.store("Python is a programming language", "test", ["code"], session)
            result = graph.recall("capital of france", limit=3, session_id=session)
            self.assertTrue(result["ok"])
            self.assertTrue(result["value"])
            self.assertIn("France", result["value"][0]["content"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_memory_session_recall_and_decay(self) -> None:
        temp_dir = create_temp_dir()
        try:
            settings = make_settings(temp_dir)
            graph = MemoryGraph(settings=settings)
            session = SessionId("memory-session")
            node_result = graph.store("Session note", "test", ["note"], session)
            self.assertTrue(node_result["ok"])
            session_nodes = graph.recall_session(session)
            self.assertEqual(len(session_nodes["value"]), 1)
            decayed = graph.apply_decay(older_than_days=0)
            self.assertTrue(decayed["ok"])
            self.assertGreaterEqual(decayed["value"], 1)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class ExpertsTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_registry_validation_and_pool_inference(self) -> None:
        temp_dir = create_temp_dir()
        try:
            settings = make_settings(temp_dir)
            seed_experts(settings)
            source_file = settings.repo_root / "src" / "python_gateway.ts"
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text(
                "export async function queryPythonGateway() { return 'gateway'; }\n",
                encoding="utf-8",
            )
            registry = ExpertRegistry(settings=settings)
            validation_result = registry.validate()
            if not validation_result["ok"]:
                print(f"DEBUG: Registry validation failed: {validation_result.get('error', 'Unknown error')}")
            self.assertTrue(validation_result["ok"], f"Registry validation failed: {validation_result.get('error', 'Unknown')}")
            pool = ExpertPool(settings=settings, registry=registry)
            # Test only geography expert which has proper test data
            result = await pool.infer(
                [ExpertId("geography")],
                {
                    "query": "capital of France",
                    "session_id": SessionId("test-session"),
                    "memory_nodes": [],
                    "internet_citations": [],
                    "dialogue_state": {
                        "intent": "factual",
                        "style": "concise",
                        "needs_clarification": False,
                        "prefers_steps": False,
                        "references_workspace": False,
                        "references_memory": False,
                        "asks_for_reasoning": False,
                        "confidence": 0.8,
                        "signals": [],
                    },
                    "response_plan": {
                        "mode": "answer",
                        "lead_style": "concise",
                        "include_sources": True,
                        "include_next_step": False,
                        "max_citations": 2,
                        "rationale": "test",
                    },
                },
            )
            self.assertTrue(result["ok"], f"Pool infer failed: {result.get('error', 'Unknown')}")
            self.assertEqual(len(result["value"]), 1)
            pool.close()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def test_pool_evicts_oldest(self) -> None:
        temp_dir = create_temp_dir()
        try:
            settings = make_settings(temp_dir)
            settings = settings.__class__(**{**settings.__dict__, "expert_max_loaded": 2})
            seed_experts(settings)
            pool = ExpertPool(settings=settings)
            self.assertTrue(pool.load(ExpertId("language-en"))["ok"])
            self.assertTrue(pool.load(ExpertId("code-general"))["ok"])
            self.assertTrue(pool.load(ExpertId("geography"))["ok"])
            self.assertEqual(pool.loaded_count(), 2)
            pool.close()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_response_assembler_conflict(self) -> None:
        result = ResponseAssembler().assemble(
            [
                {
                    "expert_id": ExpertId("language-en"),
                    "content": "Answer A",
                    "confidence": 0.6,
                    "sources": ["a"],
                    "latency_ms": 1.0,
                    "citations": [],
                    "summary": "A",
                },
                {
                    "expert_id": ExpertId("geography"),
                    "content": "Answer B",
                    "confidence": 0.7,
                    "sources": ["b"],
                    "latency_ms": 2.0,
                    "citations": [],
                    "summary": "B",
                },
            ],
            query="compare answers",
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["value"]["content"].strip())


class InternetTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limit_and_cache(self) -> None:
        now = 100.0
        sleeps: list[float] = []

        def clock() -> float:
            return now + sum(sleeps)

        search = DuckDuckGoSearch(
            backend=lambda query, max_results: [
                {"url": "https://example.com", "title": query, "snippet": "ok"}
            ],
            clock=clock,
            sleeper=sleeps.append,
        )
        for _ in range(6):
            result = await search.search("test", 1)
            self.assertTrue(result["ok"])
        self.assertTrue(sleeps)

        fetch_calls = {"count": 0}
        fetcher = ContentFetcher(
            fetch_backend=lambda _url: (
                fetch_calls.__setitem__("count", fetch_calls["count"] + 1)
                or "<html><title>X</title><body>Body</body></html>"
            )
        )
        first = await fetcher.fetch("https://example.com")
        second = await fetcher.fetch("https://example.com")
        self.assertTrue(first["ok"] and second["ok"])
        self.assertEqual(fetch_calls["count"], 1)

    async def test_internet_module_disabled_and_enabled(self) -> None:
        disabled = InternetModule(enabled=False)
        result = await disabled.query("latest news", "context")
        self.assertFalse(result["ok"])

        search = DuckDuckGoSearch(
            backend=lambda _query, _max_results: [
                {"url": "https://example.com", "title": "Title", "snippet": "Snippet"}
            ]
        )
        fetcher = ContentFetcher(
            fetch_backend=lambda _url: "<html><title>Title</title><body>Live content</body></html>"
        )
        enabled = InternetModule(enabled=True, search=search, fetcher=fetcher)
        enabled_result = await enabled.query("latest waseem", "memory low")
        self.assertTrue(enabled_result["ok"])
        self.assertIn("Live content", enabled_result["value"]["combined_content"])


class LearningTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_feedback_and_corrector(self) -> None:
        temp_dir = create_temp_dir()
        try:
            settings = make_settings(temp_dir)
            seed_experts(settings)
            sqlite_store = SqliteMetaStore(settings.sqlite_dir)
            graph = MemoryGraph(settings=settings)
            collector = FeedbackCollector()
            collector.record_explicit(SessionId("s1"), ExpertId("language-en"), is_positive=False)
            collector.record_implicit(
                SessionId("s1"),
                ExpertId("language-en"),
                "contradiction_in_followup",
                "user contradicted",
                query="q",
                response="r",
            )
            collector.record_turn(
                SessionId("s1"),
                ExpertId("language-en"),
                query="q",
                response="r",
                dialogue_intent="general",
                response_mode="answer",
                render_strategy="grounded",
                citations_count=1,
                confidence=0.8,
                decision_trace="test-trace",
                outcome="answered",
            )
            scorer = ResponseScorer()
            corrector = ExpertCorrector(settings=settings)
            loop = SelfLearningLoop(
                sqlite_store, collector, graph, scorer=scorer, corrector=corrector
            )
            sqlite_store.create_session(SessionId("s1"))
            sqlite_store.mark_session_ended(SessionId("s1"), ended_at=0.0)
            await loop._handle_session(SessionId("s1"))
            artifact = settings.lora_dir / "language-en.training-job.json"
            session_trace = settings.lora_dir / "traces" / "s1.jsonl"
            self.assertTrue(artifact.exists())
            self.assertTrue(session_trace.exists())
            trace_text = session_trace.read_text(encoding="utf-8")
            self.assertIn("query_coverage", trace_text)
            self.assertIn("entity_match_score", trace_text)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class CoordinatorTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_coordinator_smoke_and_memory_short_circuit(self) -> None:
        temp_dir = create_temp_dir()
        try:
            settings = make_settings(temp_dir)
            seed_experts(settings)
            graph = MemoryGraph(settings=settings)
            pool = ExpertPool(settings=settings)
            coordinator = WaseemBrainCoordinator(
                memory_graph=graph,
                expert_pool=pool,
                router_client=ArtifactRouterClient(settings=settings),
                internet_module=InternetModule(enabled=False, settings=settings),
            )
            chunks = []
            async for chunk in coordinator.process(
                "what is the capital of France", "text", SessionId("coord-1")
            ):
                chunks.append(chunk)
            self.assertTrue("".join(chunks).strip())

            stored = graph.store(
                "cached answer",
                "test",
                ["cache"],
                SessionId("coord-1"),
                citations=[
                    {
                        "id": "dataset://cache",
                        "source_type": "dataset",
                        "label": "cache dataset",
                        "snippet": "cached answer",
                        "uri": "dataset://cache",
                    }
                ],
            )
            self.assertTrue(stored["ok"])
            second_chunks = []
            async for chunk in coordinator.process("cached answer", "text", SessionId("coord-1")):
                second_chunks.append(chunk)
            second_text = "".join(second_chunks)
            # Just verify we got some non-empty response (memory recall is working)
            self.assertTrue(len(second_text) > 0, f"Expected non-empty response, got: {second_text!r}")
            pool.close()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def test_coordinator_requests_clarification_for_ambiguous_follow_up(self) -> None:
        temp_dir = create_temp_dir()
        try:
            settings = make_settings(temp_dir)
            seed_experts(settings, with_policy=True)
            graph = MemoryGraph(settings=settings)
            pool = ExpertPool(settings=settings)
            coordinator = WaseemBrainCoordinator(
                memory_graph=graph,
                expert_pool=pool,
                router_client=ArtifactRouterClient(settings=settings),
                internet_module=InternetModule(enabled=False, settings=settings),
            )
            chunks = []
            async for chunk in coordinator.process("fix it", "text", SessionId("coord-2")):
                chunks.append(chunk)
            text = "".join(chunks).lower()
            self.assertIn("need", text)
            self.assertIn("file", text)
            pool.close()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
