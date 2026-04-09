from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from .assistant import ActionRegistry, AssistantOrchestrator, OpenAICompatibleProvider
from .assistant.types import AssistantRequest, AssistantServerEvent
from .bootstrap import BuiltinKnowledgeBootstrap
from .config import BrainSettings, load_settings
from .coordinator import WaseemBrainCoordinator
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
from .types import SessionId, is_err


class QualityMetrics(TypedDict):
    """Quality metrics for runtime operations."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    memory_recall_hits: int
    memory_recall_misses: int
    expert_cache_hits: int
    expert_cache_misses: int
    embedding_cache_hits: int
    embedding_cache_misses: int
    fallback_chain_invocations: int
    timeout_count: int
    error_breakdown: dict[str, int]


class ComponentHealth(TypedDict):
    """Health status for a single component."""
    name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    latency_ms: float | None
    message: str
    details: dict[str, object] | None


class DeepHealthReport(TypedDict):
    """Comprehensive health check report."""
    overall_status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: float
    uptime_sec: float
    components: list[ComponentHealth]
    quality_metrics: QualityMetrics
    recommendations: list[str]


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
    capabilities: dict[str, object]
    learning: dict[str, object]
    knowledge: dict[str, object]
    router: dict[str, object]
    storage: dict[str, str]
    assistant_mode: str
    provider: dict[str, object]
    realtime_voice: dict[str, object]
    automation: dict[str, object]


class MemoryNodeSummary(TypedDict):
    id: str
    content: str
    confidence: float
    source: str


class ExpertsStatus(TypedDict):
    loaded: list[str]
    count: int


class ActionCatalogSnapshot(TypedDict):
    groups: list[dict[str, object]]


class WaseemBrainRuntime:
    """Runtime with deep health checks and quality metrics."""
    
    def __init__(
        self,
        settings: BrainSettings | None = None,
        memory_graph: MemoryGraph | None = None,
        expert_pool: ExpertPool | None = None,
        registry: ExpertRegistry | None = None,
        internet_module: InternetModule | None = None,
        coordinator: WaseemBrainCoordinator | None = None,
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
        self._coordinator = coordinator or WaseemBrainCoordinator(
            memory_graph=self._memory_graph,
            expert_pool=self._expert_pool,
            router_client=self._router_client,
            internet_module=self._internet_module,
            recall_limit=self._settings.memory_recall_limit,
            settings=self._settings,
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
        self._provider = OpenAICompatibleProvider(settings=self._settings)
        self._actions = ActionRegistry(
            settings=self._settings,
            health_snapshot=lambda: cast(dict[str, Any], self.health()),
        )
        self._assistant = AssistantOrchestrator(
            settings=self._settings,
            coordinator=self._coordinator,
            memory_graph=self._memory_graph,
            actions=self._actions,
            provider=self._provider,
        )
        
        # Quality metrics tracking
        self._metrics_lock = asyncio.Lock()
        self._request_latencies: list[float] = []
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._timeout_count = 0
        self._memory_recall_hits = 0
        self._memory_recall_misses = 0
        self._fallback_chain_invocations = 0
        self._error_breakdown: dict[str, int] = defaultdict(int)

    async def query(
        self,
        raw_input: object,
        modality_hint: str,
        session_id: SessionId,
    ) -> AsyncIterator[str]:
        request: AssistantRequest = {
            "type": "chat.submit",
            "session_id": str(session_id),
            "modality": modality_hint,
            "surface": "runtime",
            "raw_input": raw_input,
        }
        async for event in self.assistant(request):
            event_type = str(event.get("type", ""))
            if event_type == "message.delta":
                yield str(event.get("content", ""))
            elif event_type == "error":
                yield str(event.get("content", ""))
            elif event_type == "approval.required":
                yield str(event.get("content", ""))

    async def assistant(self, request: AssistantRequest) -> AsyncIterator[AssistantServerEvent]:
        self._memory_graph.ensure_session(SessionId(str(request.get("session_id", "assistant-session"))))
        async for event in self._assistant.stream(request):
            yield event

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
        if is_err(self._registry_validation):
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
            "capabilities": {
                "model_free_core": True,
                "api_key_required": False,
                "self_improvement_scope": "knowledge-only",
                "router_acceleration_optional": True,
                "default_router_backend": self._settings.router_backend,
            },
            "learning": learning_snapshot,
            "knowledge": cast(dict[str, object], knowledge_snapshot),
            "router": router_snapshot,
            "storage": storage_snapshot,
            "assistant_mode": self._settings.assistant_mode,
            "provider": cast(dict[str, object], self._provider.snapshot()),
            "realtime_voice": {
                "supported": True,
                "mode": "turn-based",
            },
            "automation": {
                "approval_required": True,
                "audit_enabled": True,
            },
        }

    def actions(self) -> ActionCatalogSnapshot:
        return {"groups": cast(list[dict[str, object]], self._actions.catalog())}

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
    
    def deep_health_check(self) -> DeepHealthReport:
        """Perform comprehensive health check of all components."""
        components: list[ComponentHealth] = []
        recommendations: list[str] = []
        
        # Check memory graph
        memory_health = self._check_memory_graph_health()
        components.append(memory_health)
        if memory_health["status"] != "healthy":
            recommendations.append(f"Memory graph: {memory_health['message']}")
        
        # Check expert pool
        expert_health = self._check_expert_pool_health()
        components.append(expert_health)
        if expert_health["status"] == "degraded":
            recommendations.append(f"Expert pool: {expert_health['message']}")
        
        # Check router
        router_health = self._check_router_health()
        components.append(router_health)
        if router_health["status"] != "healthy":
            recommendations.append(f"Router: {router_health['message']}")
        
        # Check coordinator
        coordinator_health = self._check_coordinator_health()
        components.append(coordinator_health)
        if coordinator_health["status"] != "healthy":
            recommendations.append(f"Coordinator: {coordinator_health['message']}")
        
        # Check provider (if hybrid mode)
        provider_health = self._check_provider_health()
        components.append(provider_health)
        if provider_health["status"] == "degraded" and self._settings.assistant_mode == "hybrid":
            recommendations.append(f"Provider: {provider_health['message']}")
        
        # Check storage
        storage_health = self._check_storage_health()
        components.append(storage_health)
        if storage_health["status"] != "healthy":
            recommendations.append(f"Storage: {storage_health['message']}")
        
        
        # Determine overall status
        unhealthy_count = sum(1 for c in components if c["status"] == "unhealthy")
        degraded_count = sum(1 for c in components if c["status"] == "degraded")
        
        if unhealthy_count > 0:
            overall_status: Literal["healthy", "degraded", "unhealthy"] = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        
        return {
            "overall_status": overall_status,
            "timestamp": time.time(),
            "uptime_sec": round(time.monotonic() - self._started_at, 3),
            "components": components,
            "quality_metrics": self.get_quality_metrics(),
            "recommendations": recommendations,
        }
    
    def _check_memory_graph_health(self) -> ComponentHealth:
        """Check memory graph component health."""
        start = time.monotonic()
        try:
            node_count = self._memory_graph.node_count()
            stats = self._memory_graph.stats()
            
            issues: list[str] = []
            if node_count == 0:
                issues.append("no memory nodes stored")
            
            # Check embedding cache hit rate
            from typing import cast
            cache_stats = cast(dict[str, int], stats.get("embedding_cache", {}))
            hits = cache_stats.get("hits", 0)
            misses = cache_stats.get("misses", 0)
            if hits + misses > 100:
                hit_rate = hits / (hits + misses)
                if hit_rate < 0.3:
                    issues.append(f"low embedding cache hit rate: {hit_rate:.2%}")
            
            latency_ms = (time.monotonic() - start) * 1000
            
            if issues:
                return {
                    "name": "memory_graph",
                    "status": "degraded",
                    "latency_ms": latency_ms,
                    "message": "; ".join(issues),
                    "details": {"node_count": node_count, "stats": stats},
                }
            
            return {
                "name": "memory_graph",
                "status": "healthy",
                "latency_ms": latency_ms,
                "message": f"{node_count} nodes, cache hit rate OK",
                "details": {"node_count": node_count, "stats": stats},
            }
        except Exception as exc:
            return {
                "name": "memory_graph",
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Error checking health: {exc}",
                "details": None,
            }
    
    def _check_expert_pool_health(self) -> ComponentHealth:
        """Check expert pool component health."""
        start = time.monotonic()
        try:
            loaded_count = self._expert_pool.loaded_count()
            available_count = len(self._registry.all())
            pool_status = self._expert_pool.status()
            
            issues: list[str] = []
            if available_count == 0:
                issues.append("no experts registered")
            elif loaded_count == 0 and available_count > 0:
                issues.append("no experts loaded (lazy loading)")
            
            latency_ms = (time.monotonic() - start) * 1000
            
            if issues:
                return {
                    "name": "expert_pool",
                    "status": "degraded",
                    "latency_ms": latency_ms,
                    "message": "; ".join(issues),
                    "details": {"loaded": loaded_count, "available": available_count, "status": pool_status},
                }
            
            return {
                "name": "expert_pool",
                "status": "healthy",
                "latency_ms": latency_ms,
                "message": f"{loaded_count}/{available_count} experts loaded",
                "details": {"loaded": loaded_count, "available": available_count, "status": pool_status},
            }
        except Exception as exc:
            return {
                "name": "expert_pool",
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Error checking health: {exc}",
                "details": None,
            }
    
    def _check_router_health(self) -> ComponentHealth:
        """Check router component health."""
        start = time.monotonic()
        try:
            router_artifact_ready = self._settings.router_model_path.exists()
            router_backend = self._settings.router_backend.strip().lower()
            
            issues: list[str] = []
            if not router_artifact_ready and router_backend == "local":
                issues.append("router artifact missing")
            
            if router_backend in {"auto", "grpc"} and self._router_daemon_client is not None:
                last_error = self._router_daemon_client.last_error()
                if last_error:
                    issues.append(f"router daemon error: {last_error}")
            
            latency_ms = (time.monotonic() - start) * 1000
            
            if issues:
                return {
                    "name": "router",
                    "status": "degraded",
                    "latency_ms": latency_ms,
                    "message": "; ".join(issues),
                    "details": {"backend": router_backend, "artifact_ready": router_artifact_ready},
                }
            
            return {
                "name": "router",
                "status": "healthy",
                "latency_ms": latency_ms,
                "message": f"{router_backend} backend ready",
                "details": {"backend": router_backend, "artifact_ready": router_artifact_ready},
            }
        except Exception as exc:
            return {
                "name": "router",
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Error checking health: {exc}",
                "details": None,
            }
    
    def _check_coordinator_health(self) -> ComponentHealth:
        """Check coordinator component health."""
        start = time.monotonic()
        try:
            timeout_settings = self._coordinator.timeout_settings()
            
            latency_ms = (time.monotonic() - start) * 1000
            
            return {
                "name": "coordinator",
                "status": "healthy",
                "latency_ms": latency_ms,
                "message": "Coordinator operational",
                "details": {"timeout_settings": timeout_settings},
            }
        except Exception as exc:
            return {
                "name": "coordinator",
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Error checking health: {exc}",
                "details": None,
            }
    
    def _check_provider_health(self) -> ComponentHealth:
        """Check external provider health (for hybrid mode)."""
        start = time.monotonic()
        try:
            snapshot = self._provider.snapshot()
            configured = snapshot.get("configured", False)
            reachable = snapshot.get("reachable", False)
            
            if self._settings.assistant_mode != "hybrid":
                return {
                    "name": "provider",
                    "status": "healthy",
                    "latency_ms": (time.monotonic() - start) * 1000,
                    "message": "Not applicable (local mode)",
                    "details": {"mode": "local"},
                }
            
            if not configured:
                return {
                    "name": "provider",
                    "status": "degraded",
                    "latency_ms": (time.monotonic() - start) * 1000,
                    "message": "Provider not configured",
                    "details": cast(dict[str, object], dict(snapshot)),
                }

            if not reachable:
                return {
                    "name": "provider",
                    "status": "degraded",
                    "latency_ms": (time.monotonic() - start) * 1000,
                    "message": "Provider configured but not reachable",
                    "details": cast(dict[str, object], dict(snapshot)),
                }

            return {
                "name": "provider",
                "status": "healthy",
                "latency_ms": (time.monotonic() - start) * 1000,
                "message": f"Provider {snapshot.get('model', 'unknown')} ready",
                "details": cast(dict[str, object], dict(snapshot)),
            }
        except Exception as exc:
            return {
                "name": "provider",
                "status": "degraded",
                "latency_ms": None,
                "message": f"Error checking health: {exc}",
                "details": None,
            }
    
    def _check_storage_health(self) -> ComponentHealth:
        """Check storage health."""
        start = time.monotonic()
        try:
            issues: list[str] = []
            details: dict[str, object] = {}
            
            # Check SQLite
            sqlite_path = self._settings.sqlite_dir / "metadata.db"
            if sqlite_path.exists():
                size_mb = sqlite_path.stat().st_size / (1024 * 1024)
                details["sqlite_size_mb"] = round(size_mb, 2)
                if size_mb > 100:
                    issues.append(f"SQLite database large: {size_mb:.1f}MB")
            else:
                issues.append("SQLite database not found")
            
            # Check vector index
            vector_path = self._settings.vector_index_path
            if vector_path.exists():
                details["vector_index_exists"] = True
            else:
                issues.append("Vector index not found")
            
            latency_ms = (time.monotonic() - start) * 1000
            
            if issues:
                return {
                    "name": "storage",
                    "status": "degraded",
                    "latency_ms": latency_ms,
                    "message": "; ".join(issues),
                    "details": details,
                }
            
            return {
                "name": "storage",
                "status": "healthy",
                "latency_ms": latency_ms,
                "message": "Storage operational",
                "details": details,
            }
        except Exception as exc:
            return {
                "name": "storage",
                "status": "unhealthy",
                "latency_ms": None,
                "message": f"Error checking health: {exc}",
                "details": None,
            }
    
    def get_quality_metrics(self) -> QualityMetrics:
        """Get current quality metrics."""
        # Calculate latency percentiles
        latencies = sorted(self._request_latencies[-1000:])  # Keep last 1000
        
        def percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f]) if c != f else data[f]
        
        # Get embedding cache stats from memory graph
        stats = self._memory_graph.stats()
        cache_stats = cast(dict[str, int], stats.get("embedding_cache", {}))
        
        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
            "p50_latency_ms": percentile(latencies, 50),
            "p95_latency_ms": percentile(latencies, 95),
            "p99_latency_ms": percentile(latencies, 99),
            "memory_recall_hits": self._memory_recall_hits,
            "memory_recall_misses": self._memory_recall_misses,
            "expert_cache_hits": 0,  # Would come from expert pool stats
            "expert_cache_misses": 0,
            "embedding_cache_hits": cache_stats.get("hits", 0),
            "embedding_cache_misses": cache_stats.get("misses", 0),
            "fallback_chain_invocations": self._fallback_chain_invocations,
            "timeout_count": self._timeout_count,
            "error_breakdown": dict(self._error_breakdown),
        }
    
    def record_request_metrics(
        self,
        success: bool,
        latency_ms: float,
        error_type: str | None = None,
        memory_hit: bool = False,
        fallback_used: bool = False,
        timed_out: bool = False,
    ) -> None:
        """Record metrics for a request (called by coordinator/assistant)."""
        self._total_requests += 1
        self._request_latencies.append(latency_ms)
        
        if success:
            self._successful_requests += 1
        else:
            self._failed_requests += 1
            if error_type:
                self._error_breakdown[error_type] += 1
        
        if memory_hit:
            self._memory_recall_hits += 1
        else:
            self._memory_recall_misses += 1
        
        if fallback_used:
            self._fallback_chain_invocations += 1
        
        if timed_out:
            self._timeout_count += 1
        
        # Trim latencies list to prevent unbounded growth
        if len(self._request_latencies) > 10000:
            self._request_latencies = self._request_latencies[-1000:]

    def flush_session_traces(self, session_id: SessionId) -> list[TurnTrace]:
        traces = self._coordinator.flush_session_traces(session_id)
        if not traces or not self._settings.learning_enabled:
            return traces

        for trace in traces:
            try:
                resp = str(trace.get("response", ""))
                outcome = str(trace.get("outcome", ""))
                if outcome in ("answered", "unsupported") and len(resp) > 20:
                    text_content = f"Question: {trace.get('query', '')}\nAnalysis: {resp}"
                    self._memory_graph.store(
                        content=text_content,
                        source="auto-reflection-loop",
                        tags=["auto-learned"],
                        session_id=trace["session_id"],
                        source_type="session",
                    )
            except Exception:
                pass

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
    
    def reset_metrics(self) -> None:
        """Reset all quality metrics (useful for testing/monitoring resets)."""
        self._request_latencies = []
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._timeout_count = 0
        self._memory_recall_hits = 0
        self._memory_recall_misses = 0
        self._fallback_chain_invocations = 0
        self._error_breakdown = defaultdict(int)

    def _build_router_daemon_client(self) -> RouterDaemonClient | None:
        backend = self._settings.router_backend.strip().lower()
        if backend == "local":
            return None
        return RouterDaemonClient(
            target=f"{self._settings.grpc_host}:{self._settings.grpc_port}",
            timeout_sec=self._settings.grpc_timeout_sec,
            settings=self._settings,
        )

    def _build_router_client(
        self,
        router_daemon_client: RouterDaemonClient | None,
    ) -> ArtifactRouterClient | RouterDaemonClient | HybridRouterClient:
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
        if backend == "local":
            return payload
        state = self._read_json_file(self._settings.repo_root / "tmp" / "router-daemon" / "state.json")
        if state is not None:
            host = str(state.get("host", self._settings.grpc_host))
            raw_port = state.get("port", self._settings.grpc_port)
            port = int(raw_port) if isinstance(raw_port, (int, float, str)) else self._settings.grpc_port
            reachable = self._tcp_endpoint_reachable(host, port)
            payload["daemon_state"] = "available" if reachable else "degraded"
            payload["port"] = port
            payload["pid"] = int(cast(int, state.get("pid", 0)))
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
        expert_trace_files = sorted(expert_traces_dir.glob("*.jsonl")) if expert_traces_dir.exists() else []
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

    def _refresh_response_policy(self) -> None:
        traces = self._load_trace_corpus()
        if len(traces) < 3:
            return
        policy_path = self._settings.expert_dir.parent / "response-policy.json"
        artifact = ResponsePolicyTrainer().fit(traces)
        ResponsePolicyExporter().export_model(policy_path, artifact)
        self._coordinator.reload_learned_policies()
        self._learning_last_event = (
            f"refreshed response policy from {artifact.trained_trace_count} traces"
        )

    def _load_trace_corpus(self) -> list[TurnTrace]:
        traces_dir = self._settings.lora_dir / "traces"
        if not traces_dir.exists():
            return []
        traces: list[TurnTrace] = []
        for trace_file in sorted(traces_dir.glob("*.jsonl")):
            for line in trace_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    traces.append(cast(TurnTrace, payload))
        return traces

    def _read_json_file(self, path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _tcp_endpoint_reachable(self, host: str, port: int) -> bool:
        try:
            import socket

            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    def _count_jsonl_lines(self, paths: list[Path]) -> int:
        total = 0
        for path in paths:
            try:
                total += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            except OSError:
                continue
        return total

