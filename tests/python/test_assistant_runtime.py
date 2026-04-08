from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from brain.assistant import ActionRegistry
from brain.runtime import WaseemBrainRuntime
from tests.python.support import make_settings, seed_experts


class ActionRegistryTestCase(unittest.TestCase):
    def test_catalog_preview_and_confirmation_guards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            registry = ActionRegistry(
                settings=settings,
                health_snapshot=lambda: {"ready": True, "condition_summary": "runtime healthy"},
            )

            catalog = registry.catalog()
            self.assertTrue(catalog)
            self.assertTrue(
                any(action["id"] == "system.firewall.rule" for group in catalog for action in group["actions"])
            )
            self.assertFalse(
                any(action["id"] == "chat.general" for group in catalog for action in group["actions"])
            )

            preview = registry.preview(
                "system.firewall.rule",
                {
                    "name": "Waseem Brain Allow 8080",
                    "direction": "in",
                    "action": "allow",
                    "protocol": "TCP",
                    "local_port": "8080",
                },
            )
            self.assertEqual(preview["action_id"], "system.firewall.rule")
            self.assertIn("8080", preview["summary"])

            with self.assertRaises(PermissionError):
                registry.execute(
                    "system.firewall.rule",
                    preview["inputs"],
                    surface="terminal",
                    confirmed=False,
                )

            (settings.repo_root / "src").mkdir(parents=True, exist_ok=True)
            (settings.repo_root / "src" / "assistant.ts").write_text(
                "export const assistantSocket = '/ws/assistant';\n",
                encoding="utf-8",
            )

            status = registry.execute(
                "system.runtime.status",
                {},
                surface="terminal",
                confirmed=False,
            )
            self.assertEqual(status["ready"], True)

            repo_summary = registry.execute(
                "workspace.repo.summary",
                {},
                surface="terminal",
                confirmed=False,
            )
            self.assertGreaterEqual(int(repo_summary["total_files"]), 1)

            repo_search = registry.execute(
                "workspace.repo.search",
                {"pattern": "assistantSocket"},
                surface="terminal",
                confirmed=False,
            )
            self.assertEqual(repo_search["match_count"], 1)

            file_read = registry.execute(
                "workspace.file.read",
                {"path": "src/assistant.ts", "start_line": "1", "end_line": "20"},
                surface="terminal",
                confirmed=False,
            )
            self.assertEqual(file_read["path"], "src/assistant.ts")
            self.assertTrue(any("assistantSocket" in line for line in file_read["excerpt"]))

            daemon_preview = registry.preview(
                "system.runtime.daemon.control",
                {"operation": "restart"},
            )
            self.assertEqual(daemon_preview["action_id"], "system.runtime.daemon.control")
            self.assertIn("restart", daemon_preview["summary"].lower())

            self.assertEqual(
                registry.match_text_request("show firewall rules"),
                ("system.firewall.inspect", {}),
            )
            self.assertEqual(
                registry.match_text_request("run tests for the project"),
                ("verification.fast", {}),
            )
            self.assertEqual(
                registry.match_text_request("read file src/assistant.ts"),
                ("workspace.file.read", {"path": "src/assistant.ts"}),
            )
            self.assertEqual(
                registry.match_text_request("verify project and refresh the report"),
                ("verification.project_report", {}),
            )
            self.assertIsNone(registry.match_text_request("delete random files now"))


class AssistantRuntimeTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_assistant_chat_falls_back_to_local_grounded_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            settings = settings.__class__(
                **{
                    **settings.__dict__,
                    "internet_enabled": False,
                    "model_base_url": "",
                    "model_api_key": "",
                }
            )
            seed_experts(settings)
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                events = [
                    event
                    async for event in runtime.assistant(
                        {
                            "type": "chat.submit",
                            "session_id": "assistant-1",
                            "modality": "text",
                            "input": "hello there",
                            "surface": "terminal",
                        }
                    )
                ]
            finally:
                runtime.close()

            self.assertTrue(any(event["type"] == "status" for event in events))
            done_event = next(event for event in events if event["type"] == "message.done")
            metadata = done_event["metadata"]
            self.assertEqual(metadata["local_mode"], True)
            self.assertEqual(metadata["provider"]["mode"], "local_grounded")
            self.assertTrue(str(done_event["content"]).strip())

    async def test_assistant_action_preview_emits_approval_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            seed_experts(settings)
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                events = [
                    event
                    async for event in runtime.assistant(
                        {
                            "type": "action.preview",
                            "session_id": "assistant-2",
                            "action_id": "system.firewall.rule",
                            "inputs": {
                                "name": "Waseem Brain Allow 8080",
                                "direction": "in",
                                "action": "allow",
                                "protocol": "TCP",
                                "local_port": "8080",
                            },
                            "surface": "terminal",
                        }
                    )
                ]
            finally:
                runtime.close()

            approval = next(event for event in events if event["type"] == "approval.required")
            self.assertEqual(approval["preview"]["action_id"], "system.firewall.rule")
            self.assertIn("8080", approval["preview"]["summary"])


    async def test_local_fallback_is_query_aware_for_coding_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            seed_experts(settings)
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                fallback = runtime._assistant._fallback_response("Refactor websocket retries", "coding")
            finally:
                runtime.close()

            self.assertIn("Refactor websocket retries", fallback)
            self.assertIn("workspace", fallback.lower())
            self.assertNotIn("MODEL_BASE_URL", fallback)

    async def test_assistant_identity_query_uses_local_responder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings(Path(temp_dir))
            seed_experts(settings)
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                events = [
                    event
                    async for event in runtime.assistant(
                        {
                            "type": "chat.submit",
                            "session_id": "assistant-identity",
                            "modality": "text",
                            "input": "whats ur name",
                            "surface": "terminal",
                        }
                    )
                ]
            finally:
                runtime.close()

            done_event = next(event for event in events if event["type"] == "message.done")
            self.assertIn("Waseem Brain", str(done_event["content"]))
            self.assertNotIn("COMPLETE_STRUCTURE_AND_DETAILS.md", str(done_event["content"]))

    async def test_coding_query_uses_workspace_search_responder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            settings = make_settings(temp_root)
            seed_experts(settings)
            src_dir = temp_root / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "assistant_websocket.ts").write_text(
                "export const assistantWebsocketRoute = '/ws/assistant';\n",
                encoding="utf-8",
            )
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                events = [
                    event
                    async for event in runtime.assistant(
                        {
                            "type": "chat.submit",
                            "session_id": "assistant-coding",
                            "modality": "text",
                            "input": "refactor assistant websocket route",
                            "surface": "terminal",
                        }
                    )
                ]
            finally:
                runtime.close()

            done_event = next(event for event in events if event["type"] == "message.done")
            content = str(done_event["content"])
            self.assertIn("inspected the workspace", content.lower())
            self.assertIn("assistant_websocket.ts", content)

    async def test_file_query_uses_explicit_workspace_file_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            settings = make_settings(temp_root)
            seed_experts(settings)
            brain_dir = temp_root / "brain"
            brain_dir.mkdir(parents=True, exist_ok=True)
            (brain_dir / "locale.py").write_text(
                "def detect_locale(text: str) -> str:\n    return 'en' if text else 'ur'\n",
                encoding="utf-8",
            )
            runtime = WaseemBrainRuntime(settings=settings)
            try:
                events = [
                    event
                    async for event in runtime.assistant(
                        {
                            "type": "chat.submit",
                            "session_id": "assistant-file",
                            "modality": "text",
                            "input": "explain brain/locale.py",
                            "surface": "terminal",
                        }
                    )
                ]
            finally:
                runtime.close()

            done_event = next(event for event in events if event["type"] == "message.done")
            content = str(done_event["content"])
            self.assertIn("brain/locale.py", content)
            self.assertIn("detect_locale", content)

if __name__ == "__main__":
    unittest.main()




