from __future__ import annotations

import json
import socket
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal, TypedDict, cast

from .bootstrap import BuiltinKnowledgeBootstrap
from .config import BrainSettings, load_settings
from .coordinator import LatticeBrainCoordinator, RouterClientProtocol
from .experts.pool import ExpertPool
from .experts.registry import ExpertRegistry
from .internet.module import InternetModule
from .learning.corrector import ExpertCorrector
from .learning.policy import (
    ResponsePolicyExporter,
    ResponsePolicyTrainer,
    load_response_policy,
)
from .learning.types import TurnTrace
from .memory.graph import MemoryGraph
from .router import ArtifactRouterClient, HybridRouterClient, RouterDaemonClient
from .types import ExpertId, RenderStrategy, SessionId


class HealthSnapshot(TypedDict):
    status: Literal["ok"]
    project_name: str
    condition: Literal["strong", "ready", "attention"]
    condition_summary: str
    ready: bool
    experts_loaded: int
    experts_available: int
    expert_ids: list[str]
    memory_node_count: int
    uptime_sec: float
    router_backend: str
    vector_backend: str
    components: dict[str, str]
    learning: dict[str, object]
    knowledge: dict[str, object]
    router: dict[str, object]
    storage: dict[str, str]


class MemoryNodeSummary(TypedDict):
    id: str
    content: str
    confidence: float
    source: str


class ExpertsStatus(TypedDict):
    loaded: list[str]
    count: int


class LatticeBrainRuntime:
    def __init__(
        self,
        settings: BrainSettings | None = None,
        memory_graph: MemoryGraph | None = None,
        expert_pool: ExpertPool | None = None,
        registry: ExpertRegistry | None = None,
        internet_module: InternetModule | None = None,
        coordinator: LatticeBrainCoordinator | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._memory_graph = memory_graph or MemoryGraph(settings=self._settings)
        self._registry = registry or ExpertRegistry(settings=self._settings)
        self._registry_validation = self._registry.validate()
        if self._settings.strict_runtime and not self._registry_validation["ok"]:
            raise RuntimeError(self._registry_validation["error"])
        self._router_daemon_client = self._build_router_daemon_client()
        self._router_client = self._build_router_client(self._router_daemon_client)
        self._expert_pool = expert_pool or ExpertPool(
            settings=self._settings,
            registry=self._registry,
            mapper=self._router_daemon_client,
        )
        self._internet_module = internet_module or InternetModule(settings=self._settings)
        self._coordinator = coordinator or LatticeBrainCoordinator(
            memory_graph=self._memory_graph,
            expert_pool=self._expert_pool,
            router_client=self._router_client,
            internet_module=self._internet_module,
            recall_limit=self._settings.memory_recall_limit,
        )
        self._corrector = ExpertCorrector(settings=self._settings)
        self._bootstrap = BuiltinKnowledgeBootstrap(settings=self._settings)
        self._knowledge_status = self._bootstrap.seed(self._memory_graph)
        self._learning_last_event = (
            self._knowledge_status["note"]
            if self._knowledge_status["status"] in {"seeded", "degraded"}
            else "runtime initialized"
        )
        self._started_at = time.monotonic()

    async def query(
        self,
        raw_input: object,
        modality_hint: str,
        session_id: SessionId,
    ) -> AsyncIterator[str]:
        self._memory_graph.ensure_session(session_id)
        async for token in self._coordinator.process(raw_input, modality_hint, session_id):
            yield token

    def health(self) -> HealthSnapshot:
        router_artifact_ready = self._settings.router_model_path.exists()
        response_policy_path = self._settings.expert_dir.parent / "response-policy.json"
        response_policy_ready = response_policy_path.exists()
        knowledge_snapshot = self._bootstrap.snapshot(self._memory_graph)
        router_snapshot = self._router_snapshot(router_artifact_ready)
        learning_snapshot = self._learning_snapshot(response_policy_ready)
        storage_snapshot = self._storage_snapshot(response_policy_path)
        registry_ok = bool(self._registry_validation["ok"])
        expert_ids = [str(entry["id"]) for entry in self._registry.all()]
        issues: list[str] = []
        notes: list[str] = []
        if not router_artifact_ready:
            issues.append("router artifact missing")
        if not registry_ok:
            issues.append(str(self._registry_validation["error"]))
        router_backend = self._settings.router_backend.strip().lower()
        router_daemon_state = str(router_snapshot["daemon_state"])
        if router_backend in {"auto", "grpc"}:
            if router_daemon_state == "degraded":
                message = "router daemon is unreachable"
                if router_backend == "grpc":
                    issues.append(message)
                else:
                    notes.append(f"{message}; local artifact fallback may be in use")
            elif router_daemon_state != "available":
                notes.append("router daemon state not detected")
        if knowledge_snapshot["status"] == "degraded":
            issues.append(str(knowledge_snapshot["note"]))
        elif knowledge_snapshot["status"] == "partial":
            notes.append(str(knowledge_snapshot["note"]))
        if not response_policy_ready:
            notes.append("response policy still in rule-default mode")
        if self._settings.learning_enabled and int(cast(int, learning_snapshot["trace_turns"])) < 3:
            notes.append("learning is still collecting real traces")

        if issues:
            condition: Literal["strong", "ready", "attention"] = "attention"
            condition_summary = issues[0]
        elif notes:
            condition = "ready"
            condition_summary = notes[0]
        else:
            condition = "strong"
            condition_summary = "core runtime artifacts and services look healthy"

        return {
            "status": "ok",
            "project_name": "Waseem Brain",
            "condition": condition,
            "condition_summary": condition_summary,
            "ready": not issues,
            "experts_loaded": self._expert_pool.loaded_count(),
            "experts_available": len(expert_ids),
            "expert_ids": expert_ids,
            "memory_node_count": self._memory_graph.node_count(),
            "uptime_sec": round(time.monotonic() - self._started_at, 3),
            "router_backend": self._settings.router_backend,
            "vector_backend": self._memory_graph.vector_backend_name(),
            "components": {
                "router_artifact": "ready" if router_artifact_ready else "missing",
                "response_policy": "ready" if response_policy_ready else "rule-default",
                "expert_registry": "ready" if registry_ok else "invalid",
                "router_daemon": str(router_snapshot["daemon_state"]),
                "internet": "enabled" if self._settings.internet_enabled else "disabled",
                "knowledge": str(knowledge_snapshot["status"]),
            },
            "learning": learning_snapshot,
            "knowledge": cast(dict[str, object], knowledge_snapshot),
            "router": router_snapshot,
            "storage": storage_snapshot,
        }

    def recall(self, query: str, limit: int = 5) -> list[MemoryNodeSummary]:
        if not query.strip():
            return []
        result = self._memory_graph.recall(query, limit=limit, session_id=None)
        if not result["ok"]:
            raise RuntimeError(result["error"])
        return [
            {
                "id": str(node["id"]),
                "content": node["content"],
                "confidence": node["confidence"],
                "source": node["source"],
            }
            for node in result["value"]
        ]

    def experts(self) -> ExpertsStatus:
        loaded = [str(expert_id) for expert_id in self._expert_pool.loaded_ids()]
        return {"loaded": loaded, "count": len(loaded)}

    def flush_session_traces(self, session_id: SessionId) -> list[TurnTrace]:
        traces = self._coordinator.flush_session_traces(session_id)
        if not traces or not self._settings.learning_enabled:
            return traces

        record_result = self._corrector.record_session_traces(str(session_id), traces)
        if not record_result["ok"]:
            self._learning_last_event = f"failed to persist traces for {session_id}"
            return traces

        self._learning_last_event = f"persisted {len(traces)} real trace(s) from {session_id}"
        try:
            self._refresh_response_policy()
        except Exception as exc:
            self._learning_last_event = f"response policy refresh failed: {exc}"
        return traces

    def close(self) -> None:
        self._expert_pool.close()
        self._memory_graph.close()
        if self._router_daemon_client is not None:
            self._router_daemon_client.close()

    def _build_router_daemon_client(self) -> RouterDaemonClient | None:
        backend = self._settings.router_backend.strip().lower()
        if backend == "local":
            return None
        return RouterDaemonClient(
            target=f"{self._settings.grpc_host}:{self._settings.grpc_port}",
            timeout_sec=self._settings.grpc_timeout_sec,
        )

    def _build_router_client(
        self,
        router_daemon_client: RouterDaemonClient | None,
    ) -> RouterClientProtocol:
        backend = self._settings.router_backend.strip().lower()
        artifact_client = ArtifactRouterClient(settings=self._settings)
        if router_daemon_client is None:
            return artifact_client
        if backend == "grpc":
            return router_daemon_client
        return HybridRouterClient(primary=router_daemon_client, fallback=artifact_client)

    def _router_snapshot(self, router_artifact_ready: bool) -> dict[str, object]:
        backend = self._settings.router_backend.strip().lower()
        payload: dict[str, object] = {
            "mode": self._settings.router_backend,
            "artifact": "ready" if router_artifact_ready else "missing",
            "target": f"{self._settings.grpc_host}:{self._settings.grpc_port}",
            "daemon_state": "not-needed" if backend == "local" else "untracked",
        }
        state = self._read_json_file(self._settings.repo_root / "tmp" / "router-daemon" / "state.json")
        if state is not None:
            host = str(state.get("host", self._settings.grpc_host))
            port = int(state.get("port", self._settings.grpc_port))
            reachable = self._tcp_endpoint_reachable(host, port)
            payload["daemon_state"] = "available" if reachable else "degraded"
            payload["port"] = port
            payload["pid"] = int(cast(int, state.get("pid", 0)))
            payload["port"] = port
            started_at = float(cast(float, state.get("started_at", time.time())))
            payload["uptime_sec"] = round(max(time.time() - started_at, 0.0), 3)
            if not reachable:
                payload["last_error"] = f"router daemon at {host}:{port} is not reachable"
        elif backend in {"auto", "grpc"}:
            payload["daemon_state"] = "untracked"
        if self._router_daemon_client is not None and self._router_daemon_client.last_error():
            payload["daemon_state"] = "degraded"
            payload["last_error"] = self._router_daemon_client.last_error()
        return payload

    def _learning_snapshot(self, response_policy_ready: bool) -> dict[str, object]:
        traces_dir = self._settings.lora_dir / "traces"
        expert_traces_dir = self._settings.lora_dir / "experts"
        datasets_dir = self._settings.lora_dir / "datasets"
        trace_files = sorted(traces_dir.glob("*.jsonl")) if traces_dir.exists() else []
        expert_trace_files = (
            sorted(expert_traces_dir.glob("*.jsonl")) if expert_traces_dir.exists() else []
        )
        dataset_files = sorted(datasets_dir.glob("*.jsonl")) if datasets_dir.exists() else []
        training_jobs = sorted(self._settings.lora_dir.glob("*.training-job.json"))
        trace_turns = self._count_jsonl_lines(trace_files)
        expert_trace_turns = self._count_jsonl_lines(expert_trace_files)
        trained_trace_count = 0
        policy = load_response_policy(self._settings.expert_dir.parent / "response-policy.json")
        if policy is not None:
            trained_trace_count = policy.trained_trace_count
        phase = "disabled"
        if self._settings.learning_enabled:
            if trace_turns < 3:
                phase = "collecting-real-traces"
            elif response_policy_ready and trained_trace_count >= trace_turns:
                phase = "auto-refresh-current"
            else:
                phase = "training-ready"
        return {
            "enabled": self._settings.learning_enabled,
            "backend": self._settings.learning_backend,
            "response_policy": "ready" if response_policy_ready else "rule-default",
            "trace_files": len(trace_files),
            "trace_turns": trace_turns,
            "expert_trace_files": len(expert_trace_files),
            "expert_trace_turns": expert_trace_turns,
            "training_jobs": len(training_jobs),
            "datasets": len(dataset_files),
            "trained_trace_count": trained_trace_count,
            "last_event": self._learning_last_event,
            "phase": phase,
        }

    def _storage_snapshot(self, response_policy_path: Path) -> dict[str, str]:
        return {
            "sqlite_path": str(self._settings.sqlite_dir / "metadata.db"),
            "vector_index_path": str(self._settings.vector_index_path),
            "router_artifact_path": str(self._settings.router_model_path),
            "response_policy_path": str(response_policy_path),
            "trace_dir": str(self._settings.lora_dir / "traces"),
        }

    def _count_jsonl_lines(self, paths: list[Path]) -> int:
        total = 0
        for path in paths:
            try:
                total += sum(
                    1
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            except OSError:
                continue
        return total

    def _tcp_endpoint_reachable(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    def _read_json_file(self, path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _refresh_response_policy(self) -> None:
        policy_path = self._settings.expert_dir.parent / "response-policy.json"
        trace_dir = self._settings.lora_dir / "traces"
        trace_files = sorted(trace_dir.glob("*.jsonl"))
        trace_turns = self._count_jsonl_lines(trace_files)
        if trace_turns < 3:
            return

        existing_policy = load_response_policy(policy_path)
        if existing_policy is not None and existing_policy.trained_trace_count >= trace_turns:
            return

        traces = self._load_traces(trace_files)
        if len(traces) < 3:
            return

        artifact = ResponsePolicyTrainer().fit(traces)
        ResponsePolicyExporter().export_model(policy_path, artifact)
        self._coordinator.reload_learned_policies()
        self._learning_last_event = (
            f"refreshed response policy from {artifact.trained_trace_count} real trace(s)"
        )

    def _load_traces(self, trace_files: list[Path]) -> list[TurnTrace]:
        traces: list[TurnTrace] = []
        for trace_file in trace_files:
            try:
                lines = trace_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                traces.append(
                    {
                        "session_id": SessionId(str(payload.get("session_id", ""))),
                        "expert_id": ExpertId(str(payload.get("expert_id", ""))),
                        "query": str(payload.get("query", "")),
                        "response": str(payload.get("response", "")),
                        "dialogue_intent": str(payload.get("dialogue_intent", "general")),
                        "response_mode": str(payload.get("response_mode", "answer")),
                        "render_strategy": cast(
                            RenderStrategy,
                            str(payload.get("render_strategy", "grounded")),
                        ),
                        "citations_count": int(payload.get("citations_count", 0)),
                        "has_next_step": bool(payload.get("has_next_step", False)),
                        "query_coverage": float(payload.get("query_coverage", 0.0)),
                        "entity_match_score": float(payload.get("entity_match_score", 0.0)),
                        "symbol_anchor_score": float(payload.get("symbol_anchor_score", 0.0)),
                        "response_length_tokens": int(payload.get("response_length_tokens", 0)),
                        "confidence": float(payload.get("confidence", 0.0)),
                        "decision_trace": str(payload.get("decision_trace", "")),
                        "outcome": cast(
                            Literal[
                                "answered",
                                "memory_answered",
                                "clarification_requested",
                                "unsupported",
                            ],
                            str(payload.get("outcome", "answered")),
                        ),
                        "timestamp": float(payload.get("timestamp", 0.0)),
                    }
                )
        return traces
