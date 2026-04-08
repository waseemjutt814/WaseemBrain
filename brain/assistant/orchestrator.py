from __future__ import annotations

import asyncio
import base64
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from ..config import BrainSettings, load_settings
from ..coordinator import CoordinatorTurnResult, WaseemBrainCoordinator
from ..learning.features import entity_match_score, query_coverage_score
from ..locale import LocaleEngine
from ..memory.graph import MemoryGraph
from ..normalizer import normalize
from ..types import EvidenceReference, MemoryNode, SessionId
from .actions import ActionRegistry
from .local_responder import LocalResponder, LocalResponderResult
from .providers import OpenAICompatibleProvider
from .types import AssistantMetadata, AssistantRequest, AssistantRoute, AssistantServerEvent, ProviderStatus

# Backpressure settings
MAX_CONCURRENT_REQUESTS = 10
REQUEST_TIMEOUT_SEC = 60.0
FALLBACK_CHAIN_TIMEOUT_SEC = 30.0


class AssistantBackpressureError(Exception):
    """Raised when too many concurrent requests are pending."""
    def __init__(self, current: int, max_allowed: int) -> None:
        self.current = current
        self.max_allowed = max_allowed
        super().__init__(f"Too many concurrent requests ({current}/{max_allowed}). Please retry later.")


class AssistantTimeoutError(Exception):
    """Raised when assistant processing times out."""
    def __init__(self, timeout_sec: float, stage: str) -> None:
        self.timeout_sec = timeout_sec
        self.stage = stage
        super().__init__(f"Assistant timed out after {timeout_sec}s during {stage}")


class AssistantOrchestrator:
    """Orchestrator with backpressure handling and fallback chain."""
    
    def __init__(
        self,
        *,
        settings: BrainSettings | None = None,
        coordinator: WaseemBrainCoordinator,
        memory_graph: MemoryGraph,
        actions: ActionRegistry,
        provider: OpenAICompatibleProvider,
        max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS,
        request_timeout_sec: float = REQUEST_TIMEOUT_SEC,
    ) -> None:
        self._settings = settings or load_settings()
        self._coordinator = coordinator
        self._memory_graph = memory_graph
        self._actions = actions
        self._provider = provider
        self._local_responder = LocalResponder(settings=self._settings)
        self._max_concurrent_requests = max_concurrent_requests
        self._request_timeout_sec = request_timeout_sec
        self._active_requests = 0
        self._request_lock = asyncio.Lock()

    async def stream(self, request: AssistantRequest) -> AsyncIterator[AssistantServerEvent]:
        """Stream assistant events with backpressure protection."""
        # Check backpressure
        async with self._request_lock:
            if self._active_requests >= self._max_concurrent_requests:
                yield {
                    "type": "error",
                    "content": f"Server busy. {self._active_requests} requests in progress. Please retry.",
                    "route": "general_chat",
                }
                return
            self._active_requests += 1
        
        
        try:
            # Wrap entire processing with timeout
            async for event in self._stream_with_timeout(request):
                yield event
        except asyncio.TimeoutError:
            yield {
                "type": "error",
                "content": f"Request timed out after {self._request_timeout_sec} seconds.",
                "route": "general_chat",
            }
        finally:
            async with self._request_lock:
                self._active_requests -= 1
    
    async def _stream_with_timeout(self, request: AssistantRequest) -> AsyncIterator[AssistantServerEvent]:
        """Internal stream with timeout protection."""
        request_type = str(request.get("type", "chat.submit"))
        surface = request.get("surface", "runtime")
        session_id = SessionId(str(request.get("session_id", "assistant-session")))

        if request_type == "session.update":
            yield {"type": "status", "content": "Assistant session is ready.", "route": "general_chat"}
            return

        if request_type == "action.preview":
            action_id = str(request.get("action_id", "")).strip()
            inputs = dict(request.get("inputs", {}))
            descriptor = self._actions.describe(action_id)
            preview = self._actions.preview(action_id, inputs)
            yield {"type": "status", "content": f"Previewing {descriptor['label']}.", "route": "system_action"}
            yield {
                "type": "approval.required",
                "content": f"{descriptor['label']} requires explicit confirmation before execution.",
                "route": "system_action",
                "descriptor": descriptor,
                "preview": preview,
            }
            return

        if request_type == "action.confirm":
            action_id = str(request.get("action_id", "")).strip()
            inputs = dict(request.get("inputs", {}))
            confirmed = bool(request.get("confirmed", False))
            descriptor = self._actions.describe(action_id)
            result = self._actions.execute(
                action_id,
                inputs,
                surface=surface,
                confirmed=confirmed,
            )
            content = self._render_action_result(action_id, result)
            metadata = self._build_metadata(
                route="system_action",
                provider=self._local_provider_status(),
                tools=[action_id],
                transcript="",
                citations=[],
                render_strategy="direct",
                local_mode=True,
            )
            yield {"type": "status", "content": f"Executed {descriptor['label']}.", "route": "system_action"}
            async for event in self._stream_message(content, metadata):
                yield event
            return

        modality = self._resolve_modality(request_type, str(request.get("modality", "text")))
        raw_input = self._decode_input(request, modality)
        normalized_result = normalize(raw_input, modality, session_id)
        if not normalized_result["ok"]:
            yield {"type": "error", "content": normalized_result["error"]}
            return
        signal = normalized_result["value"]
        transcript = signal.get("text", "")
        route = self._classify(signal.get("text", ""), modality)
        yield {"type": "status", "content": self._status_copy(route), "route": route}
        if modality == "voice" and transcript.strip():
            yield {"type": "transcript.partial", "content": transcript, "route": route}

        if route == "system_action":
            handled = await self._handle_text_action(signal.get("text", ""), surface)
            async for event in handled:
                yield event
            return

        local_responder_result = self._local_responder.respond(signal.get("text", ""), route)
        if local_responder_result is not None:
            async for event in self._stream_local_response(
                route=route,
                transcript=transcript,
                result=local_responder_result,
            ):
                yield event
            return

        provider_status = self._provider.snapshot()
        if (
            route in {"general_chat", "coding"}
            and self._settings.assistant_mode == "hybrid"
            and provider_status["configured"]
            and provider_status["reachable"]
        ):
            yield {"type": "tool.start", "tool": "external-provider", "content": provider_status["model"], "route": route}
            citations = self._memory_citations(signal.get("text", ""), session_id)
            if citations:
                yield {"type": "evidence", "citations": citations, "route": route}
            try:
                content = await self._provider.complete(
                    system_prompt=self._system_prompt(route),
                    user_prompt=self._provider_prompt(signal.get("text", ""), citations),
                )
                metadata = self._build_metadata(
                    route=route,
                    provider=provider_status,
                    tools=["external-provider", "memory-recall"] if citations else ["external-provider"],
                    transcript=transcript,
                    citations=citations,
                    render_strategy="direct",
                    local_mode=False,
                )
                async for event in self._stream_message(content, metadata):
                    yield event
                return
            except Exception as exc:
                yield {
                    "type": "tool.result",
                    "tool": "external-provider",
                    "content": f"Provider unavailable: {exc}",
                    "route": route,
                }

        yield {"type": "tool.start", "tool": "local-grounded", "content": "Using local grounded mode.", "route": route}
        local_result = await self._coordinator.process_signal(signal, session_id)
        citations: list[EvidenceReference] = []
        render_strategy = "direct"
        if local_result["ok"] and self._is_usable_local_result(signal.get("text", ""), local_result["value"], route):
            value = local_result["value"]
            citations = value["citations"]
            if citations:
                yield {"type": "evidence", "citations": citations, "route": route}
            metadata = self._build_metadata(
                route=route,
                provider=self._local_provider_status(),
                tools=["local-grounded"],
                transcript=transcript,
                citations=citations,
                render_strategy=value["render_strategy"],
                local_mode=True,
            )
            async for event in self._stream_message(value["content"], metadata):
                yield event
            return

        fallback = self._fallback_response(signal.get("text", ""), route)
        metadata = self._build_metadata(
            route=route,
            provider=self._local_provider_status(),
            tools=["local-grounded"],
            transcript=transcript,
            citations=[],
            render_strategy=render_strategy,
            local_mode=True,
        )
        async for event in self._stream_message(fallback, metadata):
            yield event

    async def _handle_text_action(
        self,
        query: str,
        surface: str,
    ) -> AsyncIterator[AssistantServerEvent]:
        matched = self._actions.match_text_request(query)
        if matched is None:
            guidance = (
                "System actions stay locked behind explicit previews when they can change state. Open the Actions panel to inspect runtime status, "
                "search the workspace, run verification, inspect audit logs, manage the runtime daemon, or preview a firewall rule before confirmation."
            )
            metadata = self._build_metadata(
                route="system_action",
                provider=self._local_provider_status(),
                tools=["action-catalog"],
                transcript="",
                citations=[],
                render_strategy="direct",
                local_mode=True,
            )
            async for event in self._stream_message(guidance, metadata):
                yield event
            return

        action_id, inputs = matched
        descriptor = self._actions.describe(action_id)
        if descriptor["confirmation_required"]:
            preview = self._actions.preview(action_id, inputs)
            yield {
                "type": "approval.required",
                "content": f"{descriptor['label']} is ready for preview review. Confirm it from the UI before execution.",
                "route": "system_action",
                "descriptor": descriptor,
                "preview": preview,
            }
            return

        result = self._actions.execute(action_id, inputs, surface=surface, confirmed=False)
        metadata = self._build_metadata(
            route="system_action",
            provider=self._local_provider_status(),
            tools=[action_id],
            transcript="",
            citations=[],
            render_strategy="direct",
            local_mode=True,
        )
        async for event in self._stream_message(self._render_action_result(action_id, result), metadata):
            yield event

    def _resolve_modality(self, request_type: str, raw_modality: str) -> str:
        if request_type == "voice.stop":
            return "voice"
        if request_type == "voice.submit":
            return "voice"
        return raw_modality.strip().lower() or "text"

    def _decode_input(self, request: AssistantRequest, modality: str) -> object:
        if "raw_input" in request:
            return request["raw_input"]
        if modality in {"text", "url"}:
            return str(request.get("input", ""))
        raw_base64 = str(request.get("input_base64", "")).strip()
        raw_bytes = base64.b64decode(raw_base64.encode("utf-8")) if raw_base64 else b""
        return {
            "data": raw_bytes,
            "filename": str(request.get("filename", modality)),
            "mime_type": str(request.get("mime_type", "application/octet-stream")),
            "modality": modality,
        }

    def _classify(self, text: str, modality: str) -> AssistantRoute:
        lowered = text.lower()
        if modality == "url":
            return "web_lookup"
        if modality in {"file", "voice"}:
            return "grounded_answer"
        if any(
            token in lowered
            for token in (
                "firewall",
                "sandbox",
                "runtime status",
                "runtime health",
                "runtime daemon",
                "run tests",
                "pnpm test",
                "verify project",
                "project report",
                "docker smoke",
                "compose smoke",
                "audit log",
                "action log",
            )
        ):
            return "system_action"
        if any(token in lowered for token in ("latest", "today", "news", "recent", "current")):
            return "web_lookup"
        if any(token in lowered for token in (".py", ".ts", ".tsx", ".js", ".rs", "workspace", "repo", "file", "line ")):
            return "repo_work"
        if any(token in lowered for token in ("implement", "write code", "fix bug", "refactor", "test failure", "compile")):
            return "coding"
        if any(token in lowered for token in ("what is", "who is", "where is", "capital", "how many")):
            return "grounded_answer"
        return "general_chat"

    def _status_copy(self, route: AssistantRoute) -> str:
        mapping = {
            "general_chat": "Assistant mode: conversational answer path.",
            "coding": "Assistant mode: coding answer path.",
            "repo_work": "Assistant mode: workspace-grounded repo path.",
            "grounded_answer": "Assistant mode: grounded local answer path.",
            "web_lookup": "Assistant mode: web lookup and grounding path.",
            "system_action": "Assistant mode: protected system action path.",
        }
        return mapping[route]

    def _system_prompt(self, route: AssistantRoute) -> str:
        return (
            "You are Waseem Brain, a local-first assistant. Reply naturally, stay practical, and keep answers truthful. "
            f"Current route: {route}. If local evidence is supplied, treat it as higher priority than generic assumptions."
        )

    def _provider_prompt(self, query: str, citations: list[EvidenceReference]) -> str:
        if not citations:
            return query
        evidence_lines = [f"- {citation['label']}: {citation['snippet']}" for citation in citations[:2]]
        return "\n".join([
            query,
            "",
            "Local context:",
            *evidence_lines,
        ])

    def _memory_citations(self, query: str, session_id: SessionId) -> list[EvidenceReference]:
        if not query.strip():
            return []
        recall = self._memory_graph.recall(query, limit=2, session_id=session_id)
        if not recall["ok"]:
            return []
        citations: list[EvidenceReference] = []
        for node in recall["value"]:
            for provenance in node["provenance"][:1]:
                citations.append(
                    {
                        "id": provenance["source_id"],
                        "source_type": provenance["source_type"],
                        "label": provenance["label"],
                        "snippet": provenance["snippet"],
                        "uri": provenance["uri"],
                    }
                )
        return citations[:2]

    def _is_usable_local_result(
        self,
        query: str,
        result: CoordinatorTurnResult,
        route: AssistantRoute,
    ) -> bool:
        lowered = result["content"].lower()
        if "no matching evidence" in lowered or "verified data nahi mila" in lowered:
            return False

        coverage = max(
            query_coverage_score(query, result["content"]),
            entity_match_score(query, result["content"]),
        )
        if route in {"coding", "repo_work"} and coverage < 0.15:
            return False
        if str(result["expert_id"]) == "memory-recall" and coverage < 0.2:
            return False
        if route == "grounded_answer" and result["render_strategy"] == "memory" and coverage < 0.2:
            return False
        return True

    def _fallback_response(self, query: str, route: AssistantRoute) -> str:
        text = query.strip()
        locale = LocaleEngine.detect_locale(query)
        lowered = text.lower()
        is_greeting = any(token in lowered for token in ("hello", "hi", "hey", "salam", "assalam"))
        subject = text or "this request"

        if locale == "ur":
            if is_greeting:
                return (
                    "Main local grounded mode me ready hoon. Mujhe workspace scan, file inspect, URL analysis, test runs, "
                    "aur protected system actions jaisi grounded cheezen sab se behtar aati hain."
                )
            if route in {"coding", "repo_work"}:
                return (
                    f'Is coding request par abhi mere paas seedha grounded jawab nahi nikla: "{subject}". '
                    "Agar aap file, folder, feature area, ya error share karein to main workspace inspect karke practical kaam kar sakta hoon. "
                )
            if route == "web_lookup":
                return (
                    f'Is topic par local memory se verified jawab nahi nikla: "{subject}". '
                    "Mujhe URL, source, ya fresh web direction dein to main grounded lookup ke sath jawab de sakta hoon."
                )
            if route == "system_action":
                return (
                    f'Is request ko action mode me handle karne ke liye mujhe zyada specific command chahiye: "{subject}". '
                    "Aap runtime status, project tests, report, repo search, ya kisi protected action ka exact preview mang sakte hain."
                )
            return (
                f'Abhi pure local mode me "{subject}" par generic free-form jawab dene ke bajaye main workspace, memory, files, URLs, '
                "aur protected actions ke sath best kaam karta hoon. Agar aap chahein to main is ko grounded task me convert karke handle kar sakta hoon. "
            )

        if is_greeting:
            return (
                "I am ready in local grounded mode. Point me at the workspace, a file, a URL, project verification, or a protected action "
                "and I will work from real local evidence instead of filler replies."
            )
        if route in {"coding", "repo_work"}:
            return (
                f'I do not have a grounded coding answer for "{subject}" yet. '
                "Give me the file, folder, feature area, or failing behavior and I can inspect the workspace directly. "
            )
        if route == "web_lookup":
            return (
                f'I do not have verified local evidence for "{subject}" yet. '
                "Give me a URL or a fresher lookup direction and I can answer through a grounded web path."
            )
        if route == "system_action":
            return (
                f'I need a more specific action request for "{subject}". '
                "Ask for runtime status, project tests, the project report, repo search, audit logs, or a protected action preview."
            )
        return (
            f'I do not have grounded evidence for "{subject}" yet in pure local mode. '
            "I am strongest when you point me at the workspace, a file, a URL, remembered context, or a protected local action so I can answer from real evidence. "
        )

    def _render_action_result(self, action_id: str, result: dict[str, Any]) -> str:
        if action_id == "system.runtime.status":
            ready = result.get("ready")
            condition = result.get("condition_summary", "runtime status unavailable")
            return f"Runtime ready: {ready}. {condition}"
        if action_id == "system.runtime.daemon.status":
            return str(result.get("message", "Runtime daemon status unavailable."))
        if action_id == "system.runtime.daemon.control":
            return self._render_command_payload(result)
        if action_id == "workspace.repo.summary":
            preview = result.get("modified_preview", [])
            top_level = result.get("top_level_counts", {})
            summary_lines = [
                f"Branch: {result.get('branch', 'unknown')}",
                f"Git status: {result.get('git_status', 'unknown')} ({result.get('modified_files', 0)} modified)",
                f"Files counted: {result.get('total_files', 0)}",
            ]
            if isinstance(top_level, dict) and top_level:
                top_items = list(top_level.items())[:6]
                summary_lines.append(
                    'Top-level counts: ' + ', '.join(f"{name}={count}" for name, count in top_items)
                )
            if isinstance(preview, list) and preview:
                summary_lines.append('Modified preview:')
                summary_lines.extend(str(line) for line in preview)
            return "\n".join(summary_lines)
        if action_id == "workspace.repo.search":
            matches = result.get("matches", [])
            if isinstance(matches, list) and matches:
                return "\n".join(str(line) for line in matches)
            return f"No workspace matches found for {result.get('pattern', 'the requested pattern')}."
        if action_id == "workspace.file.read":
            excerpt = result.get("excerpt", [])
            header = f"{result.get('path', 'file')} lines {result.get('start_line', 0)}-{result.get('end_line', 0)} of {result.get('total_lines', 0)}"
            if isinstance(excerpt, list) and excerpt:
                return "\n".join([header, "", *[str(line) for line in excerpt]])
            return str(result.get("message", "Workspace file is empty."))
        if action_id == "system.audit.tail":
            lines = result.get("lines", [])
            if isinstance(lines, list) and lines:
                return "\n".join(str(line) for line in lines)
            return str(result.get("message", "Audit log is empty."))
        if action_id in {"verification.fast", "verification.project_report", "deployment.docker.smoke"}:
            return self._render_command_payload(result)
        if action_id == "system.firewall.inspect":
            lines = result.get("lines", [])
            if isinstance(lines, list):
                return "\n".join(str(line) for line in lines)
        if action_id == "system.firewall.rule":
            return str(result.get("message", "Firewall rule action completed."))
        return json.dumps(result, indent=2, ensure_ascii=True)

    async def _stream_local_response(
        self,
        *,
        route: AssistantRoute,
        transcript: str,
        result: LocalResponderResult,
    ) -> AsyncIterator[AssistantServerEvent]:
        citations = result["citations"]
        if citations:
            yield {"type": "evidence", "citations": citations, "route": route}
        metadata = self._build_metadata(
            route=route,
            provider=self._local_provider_status(),
            tools=result["tools"],
            transcript=transcript,
            citations=citations,
            render_strategy="direct",
            local_mode=True,
        )
        async for event in self._stream_message(result["content"], metadata):
            yield event

    def _render_command_payload(self, result: dict[str, Any]) -> str:
        nested = result.get("result")
        if isinstance(nested, dict):
            status = nested.get("status", result.get("status", "unknown"))
            exit_code = nested.get("exit_code", "n/a")
            duration = nested.get("duration_sec", "n/a")
            output_tail = nested.get("output_tail", "")
            lines = [
                f"Status: {status}",
                f"Exit code: {exit_code}",
                f"Duration: {duration}s",
            ]
            if output_tail:
                lines.extend(["", "Output tail:", str(output_tail)])
            return "\n".join(lines)
        results = result.get("results")
        if isinstance(results, list) and results:
            lines = [
                f"Status: {result.get('status', 'unknown')}",
                str(result.get("message", "Command sequence completed.")),
            ]
            state = result.get("state")
            if isinstance(state, dict):
                lines.append(str(state.get("message", "")))
            for index, item in enumerate(results, start=1):
                if not isinstance(item, dict):
                    continue
                lines.extend(
                    [
                        "",
                        f"Step {index}: {item.get('command', 'command')}",
                        f"- status: {item.get('status', 'unknown')}",
                        f"- exit code: {item.get('exit_code', 'n/a')}",
                    ]
                )
                output_tail = item.get("output_tail")
                if output_tail:
                    lines.append(f"- output tail: {output_tail}")
            return "\n".join(lines)
        return json.dumps(result, indent=2, ensure_ascii=True)

    def _build_metadata(
        self,
        *,
        route: AssistantRoute,
        provider: ProviderStatus,
        tools: list[str],
        transcript: str,
        citations: list[EvidenceReference],
        render_strategy: str,
        local_mode: bool,
    ) -> AssistantMetadata:
        return {
            "route": route,
            "provider": provider,
            "tools": tools,
            "citations_count": len(citations),
            "render_strategy": render_strategy,
            "transcript": transcript,
            "local_mode": local_mode,
        }

    def _local_provider_status(self) -> ProviderStatus:
        return {
            "configured": False,
            "mode": "local_grounded",
            "model": "local-grounded",
            "reachable": True,
        }
    
    async def _execute_fallback_chain(
        self,
        signal: object,
        session_id: SessionId,
        route: AssistantRoute,
        transcript: str,
    ) -> AsyncIterator[AssistantServerEvent]:
        """Execute fallback chain: external provider -> coordinator -> local responder -> fallback.
        
        This provides graceful degradation when components fail.
        """
        # Step 1: Try external provider if configured and appropriate route
        if route in {"general_chat", "coding"} and self._settings.assistant_mode == "hybrid":
            provider_status = self._provider.snapshot()
            if provider_status["configured"] and provider_status["reachable"]:
                try:
                    yield {"type": "tool.start", "tool": "external-provider", "content": provider_status["model"], "route": route}
                    citations = self._memory_citations(signal.get("text", "") if isinstance(signal, dict) else "", session_id)
                    if citations:
                        yield {"type": "evidence", "citations": citations, "route": route}
                    
                    content = await asyncio.wait_for(
                        self._provider.complete(
                            system_prompt=self._system_prompt(route),
                            user_prompt=self._provider_prompt(signal.get("text", "") if isinstance(signal, dict) else "", citations),
                        ),
                        timeout=FALLBACK_CHAIN_TIMEOUT_SEC,
                    )
                    metadata = self._build_metadata(
                        route=route,
                        provider=provider_status,
                        tools=["external-provider", "memory-recall"] if citations else ["external-provider"],
                        transcript=transcript,
                        citations=citations,
                        render_strategy="direct",
                        local_mode=False,
                    )
                    async for event in self._stream_message(content, metadata):
                        yield event
                    return
                except asyncio.TimeoutError:
                    yield {
                        "type": "tool.result",
                        "tool": "external-provider",
                        "content": f"Provider timed out after {FALLBACK_CHAIN_TIMEOUT_SEC}s, falling back to local mode.",
                        "route": route,
                    }
                except Exception as exc:
                    yield {
                        "type": "tool.result",
                        "tool": "external-provider",
                        "content": f"Provider unavailable: {exc}, falling back to local mode.",
                        "route": route,
                    }
        
        # Step 2: Try local coordinator
        yield {"type": "tool.start", "tool": "local-grounded", "content": "Using local grounded mode.", "route": route}
        try:
            local_result = await asyncio.wait_for(
                self._coordinator.process_signal(signal, session_id),
                timeout=FALLBACK_CHAIN_TIMEOUT_SEC,
            )
            if local_result["ok"] and self._is_usable_local_result(
                signal.get("text", "") if isinstance(signal, dict) else "", local_result["value"], route
            ):
                value = local_result["value"]
                citations = value["citations"]
                if citations:
                    yield {"type": "evidence", "citations": citations, "route": route}
                metadata = self._build_metadata(
                    route=route,
                    provider=self._local_provider_status(),
                    tools=["local-grounded"],
                    transcript=transcript,
                    citations=citations,
                    render_strategy=value["render_strategy"],
                    local_mode=True,
                )
                async for event in self._stream_message(value["content"], metadata):
                    yield event
                return
        except asyncio.TimeoutError:
            yield {
                "type": "tool.result",
                "tool": "local-grounded",
                "content": f"Local coordinator timed out after {FALLBACK_CHAIN_TIMEOUT_SEC}s.",
                "route": route,
            }
        except Exception as exc:
            yield {
                "type": "tool.result",
                "tool": "local-grounded",
                "content": f"Local coordinator error: {exc}.",
                "route": route,
            }
        
        # Step 3: Fallback response
        fallback = self._fallback_response(signal.get("text", "") if isinstance(signal, dict) else "", route)
        metadata = self._build_metadata(
            route=route,
            provider=self._local_provider_status(),
            tools=["fallback"],
            transcript=transcript,
            citations=[],
            render_strategy="direct",
            local_mode=True,
        )
        async for event in self._stream_message(fallback, metadata):
            yield event
    
    def get_backpressure_stats(self) -> dict[str, int | float]:
        """Return backpressure statistics for monitoring."""
        return {
            "active_requests": self._active_requests,
            "max_concurrent_requests": self._max_concurrent_requests,
            "request_timeout_sec": self._request_timeout_sec,
        }

    async def _stream_message(
        self,
        content: str,
        metadata: AssistantMetadata,
    ) -> AsyncIterator[AssistantServerEvent]:
        for token in content.split():
            yield {"type": "message.delta", "content": f"{token} ", "route": metadata["route"]}
        yield {"type": "message.done", "content": content, "route": metadata["route"], "metadata": metadata}








