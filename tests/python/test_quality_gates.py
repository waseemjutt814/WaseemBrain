from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.guard_no_placeholders import guard_repo


def _seed_repo(root: Path) -> None:
    (root / "brain").mkdir(parents=True, exist_ok=True)
    (root / "interface" / "src").mkdir(parents=True, exist_ok=True)
    (root / "router-daemon" / "src").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    expert_root = root / "experts" / "base" / "language-en"
    expert_root.mkdir(parents=True, exist_ok=True)

    (root / "brain" / "runtime.py").write_text("print('runtime-ok')\n", encoding="utf-8")
    (root / "interface" / "src" / "server.ts").write_text("export {};\n", encoding="utf-8")
    (root / "router-daemon" / "src" / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
    (root / "scripts" / "coordinator_bridge.py").write_text("print('bridge-ok')\n", encoding="utf-8")
    (root / "scripts" / "create_expert.py").write_text("print('expert-ok')\n", encoding="utf-8")
    (root / "scripts" / "train_router.py").write_text("print('train-ok')\n", encoding="utf-8")

    (expert_root / "manifest.json").write_text(
        json.dumps({"kind": "grounded-language", "requires_evidence": True}, indent=2),
        encoding="utf-8",
    )
    (root / "experts" / "registry.json").write_text(
        json.dumps(
            [
                {
                    "id": "language-en",
                    "kind": "grounded-language",
                    "artifact_root": "language-en",
                    "artifacts": [{"name": "manifest", "path": "manifest.json", "kind": "config"}],
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "experts" / "router.json").write_text(
        json.dumps(
            {
                "labels": ["language-en"],
                "feature_count": 8,
                "expert_weights": [[1.0] * 8],
                "expert_bias": [0.0],
                "internet_weights": [0.0] * 8,
                "internet_bias": 0.0,
                "confidence_floor": 0.5,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


class PlaceholderGuardTestCase(unittest.TestCase):
    def test_guard_accepts_clean_real_mode_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _seed_repo(root)
            self.assertEqual(guard_repo(root), [])

    def test_guard_rejects_stub_runtime_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _seed_repo(root)
            (root / "interface" / "src" / "server.ts").write_text(
                "function createStubGateway() { return null; }\n",
                encoding="utf-8",
            )
            errors = guard_repo(root)
            self.assertTrue(errors)
            self.assertTrue(any("stub gateway bootstrap" in error for error in errors))

    def test_guard_rejects_checked_in_onnx_placeholder_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _seed_repo(root)
            artifact_root = root / "experts" / "base" / "language-en"
            (artifact_root / "language-en.onnx").write_bytes(b"tiny")
            payload = json.loads((root / "experts" / "registry.json").read_text(encoding="utf-8"))
            payload[0]["artifacts"].append(
                {"name": "model", "path": "language-en.onnx", "kind": "model"}
            )
            (root / "experts" / "registry.json").write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
            errors = guard_repo(root)
            self.assertTrue(any("ONNX" in error for error in errors))

    def test_guard_accepts_file_based_python_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _seed_repo(root)
            module_path = root / "experts" / "base" / "cybersecurity_expert.py"
            module_path.write_text(
                "class CybersecurityExpert:\n    capability = 'network-security'\n",
                encoding="utf-8",
            )
            payload = json.loads((root / "experts" / "registry.json").read_text(encoding="utf-8"))
            payload.append(
                {
                    "id": "cybersecurity",
                    "kind": "security-knowledge",
                    "artifact_root": "cybersecurity_expert",
                    "artifacts": [
                        {
                            "name": "module",
                            "path": "cybersecurity_expert.py",
                            "kind": "python-module",
                        }
                    ],
                }
            )
            (root / "experts" / "registry.json").write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
            self.assertEqual(guard_repo(root), [])


if __name__ == "__main__":
    unittest.main()
