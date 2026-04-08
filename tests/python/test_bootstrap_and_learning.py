from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from brain.learning.policy import load_response_policy
from brain.runtime import WaseemBrainRuntime
from brain.types import SessionId
from tests.python.support import make_settings, seed_experts


class BootstrapAndLearningRuntimeTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_seeds_builtin_knowledge_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            seed_experts(settings)
            bootstrap_dir = settings.expert_dir.parent / "bootstrap" / "generated"
            bootstrap_dir.mkdir(parents=True, exist_ok=True)
            (bootstrap_dir / "mini-knowledge.json").write_text(
                json.dumps(
                    {
                        "dataset_id": "mini-knowledge",
                        "name": "Mini Knowledge",
                        "version": "1",
                        "cards": [
                            {
                                "id": "greeting",
                                "title": "Greeting",
                                "tags": ["greeting"],
                                "content": (
                                    "Hello. This runtime can answer grounded questions, help with "
                                    "coding, and explain checked-in concepts."
                                ),
                                "source_label": "Mini Knowledge Greeting",
                                "source_uri": "https://example.com/mini-greeting",
                                "source_type": "internet",
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            runtime = WaseemBrainRuntime(settings=settings)
            try:
                health = runtime.health()
                self.assertEqual(health["knowledge"]["datasets"], 1)
                self.assertEqual(health["knowledge"]["cards"], 1)
                self.assertEqual(health["knowledge"]["seeded_cards"], 1)
                self.assertEqual(health["components"]["knowledge"], "ready")
                self.assertGreaterEqual(health["memory_node_count"], 1)

                recall = runtime.recall("hello grounded coding questions", limit=3)
                self.assertTrue(recall)
                self.assertIn("grounded questions", recall[0]["content"].lower())
            finally:
                runtime.close()

    async def test_runtime_persists_real_traces_and_refreshes_response_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            settings = settings.__class__(**{**settings.__dict__, "internet_enabled": False})
            seed_experts(settings)
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                for index, query in enumerate(
                    [
                        "what is the capital of France",
                        "what is the capital of Pakistan",
                        "what is the capital of Japan",
                    ]
                ):
                    session_id = SessionId(f"learn-{index}")
                    async for _ in runtime.query(query, "text", session_id):
                        pass
                    traces = runtime.flush_session_traces(session_id)
                    self.assertEqual(len(traces), 1)

                policy_path = settings.expert_dir.parent / "response-policy.json"
                self.assertTrue(policy_path.exists())
                policy = load_response_policy(policy_path)
                self.assertIsNotNone(policy)
                assert policy is not None
                self.assertGreaterEqual(policy.trained_trace_count, 3)

                trace_files = sorted((settings.lora_dir / "traces").glob("*.jsonl"))
                self.assertEqual(len(trace_files), 3)

                health = runtime.health()
                self.assertEqual(health["learning"]["phase"], "auto-refresh-current")
                self.assertEqual(health["learning"]["trained_trace_count"], 3)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
