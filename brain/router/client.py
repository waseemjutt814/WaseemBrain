from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, cast

from ..config import BrainSettings, load_settings
from ..types import EmotionContext, ExpertId, NormalizedSignal, Result, RouterDecision, err, ok
from .generated import router_pb2 as _router_pb2
from .generated import router_pb2_grpc as _router_pb2_grpc
from .model import RouterArtifact, RouterArtifactError

router_pb2 = cast(Any, _router_pb2)
router_pb2_grpc = cast(Any, _router_pb2_grpc)


class RouterClientProtocol(Protocol):
    """Protocol for router client implementations."""
    
    def decide(
        self,
        signal: NormalizedSignal,
        emotion_context: EmotionContext,
    ) -> Result[RouterDecision, str]: ...
    
    def close(self) -> None: ...


class ArtifactRouterClient:
    """Router client using local artifact file with validation."""
    
    def __init__(
        self,
        settings: BrainSettings | None = None,
        artifact_path: Path | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._artifact_path = artifact_path or self._settings.router_model_path
        self._artifact: RouterArtifact | None = None
        self._load_error: str | None = None

    def decide(
        self,
        signal: NormalizedSignal,
        emotion_context: EmotionContext,
    ) -> Result[RouterDecision, str]:
        del emotion_context
        try:
            artifact = self._ensure_artifact()
        except RouterArtifactError as exc:
            self._load_error = str(exc)
            return err(f"Router artifact validation failed: {exc}")
        except Exception as exc:
            self._load_error = str(exc)
            return err(f"Router artifact unavailable at {self._artifact_path}: {exc}")
        return ok(artifact.decide(signal.get("text", "")))
    
    def last_error(self) -> str | None:
        """Return the last error encountered during artifact load."""
        return self._load_error
    
    def artifact_info(self) -> dict[str, object]:
        """Return information about the loaded artifact."""
        if self._artifact is None:
            return {"loaded": False, "error": self._load_error}
        return {
            "loaded": True,
            "version": self._artifact.version,
            "checksum": self._artifact.checksum,
            "sparsity": self._artifact.sparsity(),
            "memory_savings": self._artifact.memory_savings(),
            "labels": list(self._artifact.labels),
        }

    def close(self) -> None:
        self._artifact = None

    def _ensure_artifact(self) -> RouterArtifact:
        if self._artifact is None:
            self._artifact = RouterArtifact.load(self._artifact_path)
        return self._artifact


class RouterDaemonClient:
    """Router client connecting to gRPC daemon with configurable cooldown."""
    
    def __init__(
        self,
        target: str,
        timeout_sec: float = 0.5,
        cooldown_sec: float | None = None,
        settings: BrainSettings | None = None,
        channel_factory: Callable[[str], object] | None = None,
    ) -> None:
        self._target = target
        self._timeout_sec = timeout_sec
        # Use settings for cooldown if not explicitly provided
        if cooldown_sec is not None:
            self._cooldown_sec = cooldown_sec
        else:
            _settings = settings or load_settings()
            self._cooldown_sec = _settings.router_daemon_cooldown_sec
        self._channel_factory = channel_factory or self._default_channel_factory
        self._channel: object | None = None
        self._router_stub: Any | None = None
        self._expert_stub: Any | None = None
        self._disabled_until = 0.0
        self._last_error = ""

    def decide(
        self,
        signal: NormalizedSignal,
        emotion_context: EmotionContext,
    ) -> Result[RouterDecision, str]:
        availability = self._check_availability()
        if availability is not None:
            return err(availability)
        try:
            response = self._ensure_router_stub().Decide(
                router_pb2.RouterRequest(
                    text=signal.get("text", ""),
                    modality=signal.get("modality", "text"),
                    session_id=str(signal.get("session_id", "anonymous-session")),
                    emotion_valence=float(emotion_context["valence"]),
                    emotion_arousal=float(emotion_context["arousal"]),
                    emotion_primary=str(emotion_context["primary_emotion"]),
                ),
                timeout=self._timeout_sec,
            )
        except Exception as exc:
            self._mark_unavailable(exc)
            return err(f"Router daemon unavailable at {self._target}: {exc}")

        self._disabled_until = 0.0
        self._last_error = ""
        return ok(
            {
                "experts_needed": [ExpertId(expert_id) for expert_id in response.expert_ids],
                "check_memory_first": bool(response.check_memory_first),
                "internet_needed": bool(response.internet_needed),
                "confidence": float(response.confidence),
                "reasoning_trace": str(response.reasoning_trace),
            }
        )

    def map_expert(self, expert_id: ExpertId, file_path: Path) -> Result[bool, str]:
        availability = self._check_availability()
        if availability is not None:
            return err(availability)
        try:
            response = self._ensure_expert_stub().MapExpert(
                router_pb2.MapRequest(
                    expert_id=str(expert_id),
                    file_path=str(file_path),
                ),
                timeout=self._timeout_sec,
            )
        except Exception as exc:
            self._mark_unavailable(exc)
            return err(f"Expert mapping failed for {expert_id}: {exc}")
        self._disabled_until = 0.0
        self._last_error = ""
        return ok(bool(response.mapped))

    def evict_expert(self, expert_id: ExpertId) -> Result[bool, str]:
        availability = self._check_availability()
        if availability is not None:
            return err(availability)
        try:
            response = self._ensure_expert_stub().EvictExpert(
                router_pb2.EvictRequest(expert_id=str(expert_id)),
                timeout=self._timeout_sec,
            )
        except Exception as exc:
            self._mark_unavailable(exc)
            return err(f"Expert eviction failed for {expert_id}: {exc}")
        self._disabled_until = 0.0
        self._last_error = ""
        return ok(bool(response.evicted))

    def close(self) -> None:
        channel = self._channel
        if channel is not None and hasattr(channel, "close"):
            channel.close()
        self._channel = None
        self._router_stub = None
        self._expert_stub = None

    def last_error(self) -> str:
        return self._last_error

    def target(self) -> str:
        return self._target

    def _check_availability(self) -> str | None:
        if time.monotonic() < self._disabled_until:
            return self._last_error or f"Router daemon cooldown active for {self._target}"
        return None

    def _mark_unavailable(self, error: Exception) -> None:
        self._disabled_until = time.monotonic() + self._cooldown_sec
        self._last_error = f"Router daemon unavailable at {self._target}: {error}"

    def _ensure_router_stub(self) -> Any:
        if self._router_stub is None:
            self._router_stub = router_pb2_grpc.RouterServiceStub(self._ensure_channel())
        return self._router_stub

    def _ensure_expert_stub(self) -> Any:
        if self._expert_stub is None:
            self._expert_stub = router_pb2_grpc.ExpertServiceStub(self._ensure_channel())
        return self._expert_stub

    def _ensure_channel(self) -> object:
        if self._channel is None:
            self._channel = self._channel_factory(self._target)
        return self._channel

    def _default_channel_factory(self, target: str) -> object:
        try:
            import grpc
        except Exception as exc:
            raise RuntimeError(f"grpc is not installed: {exc}") from exc
        return grpc.insecure_channel(target)


class HybridRouterClient:
    """Router client with primary daemon and local fallback."""
    
    def __init__(self, primary: RouterDaemonClient, fallback: RouterClientProtocol) -> None:
        self._primary = primary
        self._fallback = fallback

    def decide(
        self,
        signal: NormalizedSignal,
        emotion_context: EmotionContext,
    ) -> Result[RouterDecision, str]:
        primary_result = self._primary.decide(signal, emotion_context)
        if primary_result["ok"]:
            return primary_result
        # Fallback is guaranteed to exist by type
        return self._fallback.decide(signal, emotion_context)

    def close(self) -> None:
        self._primary.close()
        if hasattr(self._fallback, 'close'):
            self._fallback.close()
