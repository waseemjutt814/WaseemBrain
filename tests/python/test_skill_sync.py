from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.sync_codex_skills import SOURCE_SKILLS, sync_all_skills
from scripts.validate_codex_skills import validate_skills_root


class SkillSyncTestCase(unittest.TestCase):
    def test_sync_and_validate_generated_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "skills"
            synced_count = sync_all_skills(output_root)

            self.assertEqual(synced_count, len(SOURCE_SKILLS))
            self.assertEqual(validate_skills_root(output_root), [])

    def test_generated_skill_references_match_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "skills"
            sync_all_skills(output_root)

            orchestrator = output_root / "waseem-brain-build-orchestrator"
            memory_skill = output_root / "waseem-brain-memory-graph"
            quality_skill = output_root / "waseem-brain-quality-gates"

            self.assertTrue((orchestrator / "references" / "source-skills.md").exists())
            self.assertFalse((orchestrator / "references" / "component-guide.md").exists())
            self.assertTrue((memory_skill / "references" / "component-guide.md").exists())
            self.assertTrue((memory_skill / "references" / "anti-placeholder.md").exists())
            self.assertTrue((memory_skill / "references" / "runtime-expectations.md").exists())
            self.assertTrue((memory_skill / "references" / "brain-plan.md").exists())
            self.assertIn(
                "allow_implicit_invocation: false",
                (memory_skill / "agents" / "openai.yaml").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "python scripts/guard_no_placeholders.py",
                (quality_skill / "SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "references/brain-plan.md",
                (quality_skill / "SKILL.md").read_text(encoding="utf-8"),
            )

    def test_validation_ignores_unrelated_skills_in_shared_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "skills"
            sync_all_skills(output_root)
            unrelated_skill = output_root / "system-skill"
            unrelated_skill.mkdir(parents=True)

            self.assertEqual(validate_skills_root(output_root), [])


if __name__ == "__main__":
    unittest.main()
