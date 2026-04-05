from __future__ import annotations

import unittest

from brain.types import EmbeddingVector, ExpertId, SessionId, err, is_err, is_ok, ok


class TypesTestCase(unittest.TestCase):
    def test_branded_types_accept_expected_primitive(self) -> None:
        session_id = SessionId("session-1")
        expert_id = ExpertId("expert-1")
        vector = EmbeddingVector([1, 2, 3])
        self.assertIsInstance(session_id, SessionId)
        self.assertIsInstance(expert_id, ExpertId)
        self.assertIsInstance(vector, EmbeddingVector)

    def test_branded_types_reject_wrong_primitive(self) -> None:
        with self.assertRaises(TypeError):
            SessionId(123)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            EmbeddingVector("abc")  # type: ignore[arg-type]

    def test_result_helpers(self) -> None:
        good = ok(123)
        bad = err("boom")
        self.assertTrue(is_ok(good))
        self.assertTrue(is_err(bad))
        self.assertEqual(good["value"], 123)
        self.assertEqual(bad["error"], "boom")


if __name__ == "__main__":
    unittest.main()
