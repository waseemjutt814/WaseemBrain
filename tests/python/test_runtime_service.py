from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from brain.runtime import WaseemBrainRuntime
from brain.types import SessionId
from tests.python.support import make_settings, seed_experts


class RuntimeServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_health_query_recall_and_experts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            settings = settings.__class__(
                **{
                    **settings.__dict__,
                    "internet_enabled": False,
                }
            )
            seed_experts(settings)
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                initial_health = runtime.health()
                self.assertEqual(initial_health["memory_node_count"], 0)
                self.assertEqual(initial_health["experts_loaded"], 0)

                chunks = []
                async for chunk in runtime.query(
                    "what is the capital of France",
                    "text",
                    SessionId("runtime-1"),
                ):
                    chunks.append(chunk)
                self.assertTrue("".join(chunks).strip())

                health = runtime.health()
                self.assertGreaterEqual(health["memory_node_count"], 1)
                self.assertGreaterEqual(health["experts_loaded"], 1)

                experts = runtime.experts()
                self.assertIn("geography", experts["loaded"])

                recall = runtime.recall("France")
                self.assertTrue(recall)
                self.assertIn("france", recall[0]["content"].lower())
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
