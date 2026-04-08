from __future__ import annotations

import os
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Configuration validation failed: {'; '.join(errors)}")


class SecureAPIKey:
    """Secure wrapper for API keys that prevents accidental logging/exposure."""
    __slots__ = ('_key', '_masked')
    
    def __init__(self, key: str) -> None:
        self._key = key
        self._masked = self._mask_key(key)
    
    def _mask_key(self, key: str) -> str:
        """Create a masked version for logging/display."""
        if not key:
            return "(not set)"
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"
    
    def get(self) -> str:
        """Get the actual API key value."""
        return self._key
    
    def __repr__(self) -> str:
        return f"SecureAPIKey({self._masked})"
    
    def __str__(self) -> str:
        return self._masked
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, SecureAPIKey):
            return self._key == other._key
        return False
    
    def __hash__(self) -> int:
        return hash(self._key)
    
    def __bool__(self) -> bool:
        return bool(self._key)


def _read_bool(raw_value: str, *, default: bool) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _read_int(raw_value: str, *, default: int) -> int:
    try:
        return int(raw_value.strip())
    except (TypeError, ValueError):
        return default


def _read_float(raw_value: str, *, default: float) -> float:
    try:
        return float(raw_value.strip())
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class BrainSettings:
    repo_root: Path
    expert_dir: Path
    expert_registry_path: Path
    lora_dir: Path
    chroma_dir: Path
    sqlite_dir: Path
    vector_index_path: Path
    embedding_backend: str
    embedding_model_name: str
    embedding_dimensions: int
    memory_vector_backend: str
    learning_backend: str
    internet_enabled: bool
    internet_max_requests_per_query: int
    internet_cache_ttl_seconds: int
    internet_allowed_domains: tuple[str, ...]
    http_timeout_sec: float
    http_user_agent: str
    http_allow_insecure_tls: bool
    assistant_mode: str
    model_provider: str
    model_base_url: str
    model_name: str
    model_api_key: SecureAPIKey  # Changed from str to SecureAPIKey
    whisper_model: str
    voice_sample_rate: int
    voice_tts_enabled: bool
    expert_max_loaded: int
    expert_idle_timeout_sec: int
    memory_recall_limit: int
    memory_decay_days: int
    learning_enabled: bool
    learning_min_signal_strength: float
    learning_correction_batch_size: int
    router_backend: str
    router_model_path: Path
    router_confidence_threshold: float
    router_daemon_cooldown_sec: float
    grpc_host: str
    grpc_port: int
    grpc_timeout_sec: float
    api_port: int
    log_level: str
    max_citations: int
    strict_runtime: bool
    action_audit_path: Path
    # Super Agent Settings
    super_agent_enabled: bool
    super_agent_reasoning_depth: str
    super_agent_auto_approve_safe: bool
    super_agent_max_execution_time_sec: float
    super_agent_learning_enabled: bool
    super_agent_safety_strict_mode: bool
    
    def validate(self) -> list[str]:
        """Validate settings and return list of errors (empty if valid)."""
        errors: list[str] = []
        
        # Validate paths exist or can be created
        if not self.repo_root.exists():
            errors.append(f"REPO_ROOT does not exist: {self.repo_root}")
        
        # Validate numeric ranges
        if self.embedding_dimensions <= 0:
            errors.append(f"EMBEDDING_DIMENSIONS must be positive: {self.embedding_dimensions}")
        if self.embedding_dimensions > 4096:
            errors.append(f"EMBEDDING_DIMENSIONS seems too large: {self.embedding_dimensions}")
        
        if not 0.0 <= self.router_confidence_threshold <= 1.0:
            errors.append(f"ROUTER_CONFIDENCE_THRESHOLD must be between 0 and 1: {self.router_confidence_threshold}")
        
        if self.http_timeout_sec <= 0:
            errors.append(f"HTTP_TIMEOUT_SEC must be positive: {self.http_timeout_sec}")
        if self.http_timeout_sec > 300:
            errors.append(f"HTTP_TIMEOUT_SEC seems too large: {self.http_timeout_sec}")
        
        if self.expert_max_loaded <= 0:
            errors.append(f"EXPERT_MAX_LOADED must be positive: {self.expert_max_loaded}")
        if self.expert_max_loaded > 20:
            errors.append(f"EXPERT_MAX_LOADED may cause memory issues: {self.expert_max_loaded}")
        
        if self.expert_idle_timeout_sec < 0:
            errors.append(f"EXPERT_IDLE_TIMEOUT_SEC cannot be negative: {self.expert_idle_timeout_sec}")
        
        if self.memory_recall_limit <= 0:
            errors.append(f"MEMORY_RECALL_LIMIT must be positive: {self.memory_recall_limit}")
        
        if self.memory_decay_days <= 0:
            errors.append(f"MEMORY_DECAY_DAYS must be positive: {self.memory_decay_days}")
        
        if not 0.0 <= self.learning_min_signal_strength <= 1.0:
            errors.append(f"LEARNING_MIN_SIGNAL_STRENGTH must be between 0 and 1: {self.learning_min_signal_strength}")
        
        if self.grpc_port <= 0 or self.grpc_port > 65535:
            errors.append(f"GRPC_PORT must be valid port (1-65535): {self.grpc_port}")
        if self.api_port <= 0 or self.api_port > 65535:
            errors.append(f"API_PORT must be valid port (1-65535): {self.api_port}")
        
        # Validate enum-like fields
        valid_assistant_modes = {"local", "hybrid"}
        if self.assistant_mode not in valid_assistant_modes:
            errors.append(f"ASSISTANT_MODE must be one of {valid_assistant_modes}: {self.assistant_mode}")
        
        valid_embedding_backends = {"auto", "sentence-transformers", "hash"}
        if self.embedding_backend not in valid_embedding_backends:
            errors.append(f"EMBEDDING_BACKEND must be one of {valid_embedding_backends}: {self.embedding_backend}")
        
        valid_vector_backends = {"auto", "hnsw", "portable", "text-only"}
        if self.memory_vector_backend not in valid_vector_backends:
            errors.append(f"MEMORY_VECTOR_BACKEND must be one of {valid_vector_backends}: {self.memory_vector_backend}")
        
        valid_reasoning_depths = {"shallow", "medium", "deep"}
        if self.super_agent_reasoning_depth not in valid_reasoning_depths:
            errors.append(f"SUPER_AGENT_REASONING_DEPTH must be one of {valid_reasoning_depths}: {self.super_agent_reasoning_depth}")
        
        # Validate model configuration consistency
        if self.assistant_mode == "hybrid" and not self.model_api_key:
            errors.append("ASSISTANT_MODE=hybrid requires MODEL_API_KEY to be set")
        
        if self.model_provider == "openai_compatible" and self.assistant_mode == "hybrid":
            if not self.model_base_url and not self.model_api_key:
                errors.append("Hybrid mode with openai_compatible provider requires MODEL_BASE_URL or MODEL_API_KEY")
        
        
        # Validate log level
        valid_log_levels = {"debug", "info", "warning", "error", "critical"}
        if self.log_level.lower() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of {valid_log_levels}: {self.log_level}")
        
        
        return errors
    
    def safe_dict(self) -> dict[str, Any]:
        """Return settings as dict with sensitive values masked."""
        return {
            "repo_root": str(self.repo_root),
            "expert_dir": str(self.expert_dir),
            "embedding_backend": self.embedding_backend,
            "embedding_model_name": self.embedding_model_name,
            "embedding_dimensions": self.embedding_dimensions,
            "memory_vector_backend": self.memory_vector_backend,
            "internet_enabled": self.internet_enabled,
            "assistant_mode": self.assistant_mode,
            "model_provider": self.model_provider,
            "model_base_url": self.model_base_url,
            "model_name": self.model_name,
            "model_api_key": str(self.model_api_key),  # Masked via SecureAPIKey.__str__
            "expert_max_loaded": self.expert_max_loaded,
            "grpc_host": self.grpc_host,
            "grpc_port": self.grpc_port,
            "api_port": self.api_port,
            "log_level": self.log_level,
            "super_agent_enabled": self.super_agent_enabled,
        }


def load_settings(env: Mapping[str, str] | None = None) -> BrainSettings:
    source = os.environ if env is None else env
    raw_domains = source.get("INTERNET_ALLOWED_DOMAINS", "")
    allowed_domains = tuple(domain.strip() for domain in raw_domains.split(",") if domain.strip())
    repo_root = Path(source.get("REPO_ROOT", Path.cwd()))
    expert_dir = Path(source.get("EXPERT_DIR", "./experts/base"))
    chroma_dir = Path(source.get("CHROMA_DIR", "./data/chroma"))

    return BrainSettings(
        repo_root=repo_root,
        expert_dir=expert_dir,
        expert_registry_path=Path(
            source.get("EXPERT_REGISTRY_PATH", str(expert_dir.parent / "registry.json"))
        ),
        lora_dir=Path(source.get("LORA_DIR", "./experts/lora")),
        chroma_dir=chroma_dir,
        sqlite_dir=Path(source.get("SQLITE_DIR", "./data/sqlite")),
        vector_index_path=Path(source.get("VECTOR_INDEX_PATH", str(chroma_dir / "memory.index"))),
        embedding_backend=source.get("EMBEDDING_BACKEND", "auto"),
        embedding_model_name=source.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
        embedding_dimensions=_read_int(source.get("EMBEDDING_DIMENSIONS", "384"), default=384),
        memory_vector_backend=source.get("MEMORY_VECTOR_BACKEND", "auto"),
        learning_backend=source.get("LEARNING_BACKEND", "auto"),
        internet_enabled=_read_bool(source.get("INTERNET_ENABLED", "true"), default=True),
        internet_max_requests_per_query=_read_int(
            source.get("INTERNET_MAX_REQUESTS_PER_QUERY", "5"), default=5
        ),
        internet_cache_ttl_seconds=_read_int(
            source.get("INTERNET_CACHE_TTL_SECONDS", "3600"), default=3600
        ),
        internet_allowed_domains=allowed_domains,
        http_timeout_sec=_read_float(source.get("HTTP_TIMEOUT_SEC", "10.0"), default=10.0),
        http_user_agent=source.get("HTTP_USER_AGENT", "WaseemBrain/0.1"),
        http_allow_insecure_tls=_read_bool(
            source.get("HTTP_ALLOW_INSECURE_TLS", "false"),
            default=False,
        ),
        assistant_mode=source.get("ASSISTANT_MODE", "local").strip().lower() or "local",
        model_provider=source.get("MODEL_PROVIDER", "openai_compatible").strip().lower()
        or "openai_compatible",
        model_base_url=source.get("MODEL_BASE_URL", "").strip(),
        model_name=source.get("MODEL_NAME", "gpt-4o-mini").strip() or "gpt-4o-mini",
        model_api_key=SecureAPIKey(source.get("MODEL_API_KEY", "").strip()),
        whisper_model=source.get("WHISPER_MODEL", "small"),
        voice_sample_rate=_read_int(source.get("VOICE_SAMPLE_RATE", "16000"), default=16000),
        voice_tts_enabled=_read_bool(source.get("VOICE_TTS_ENABLED", "true"), default=True),
        expert_max_loaded=_read_int(source.get("EXPERT_MAX_LOADED", "3"), default=3),
        expert_idle_timeout_sec=_read_int(source.get("EXPERT_IDLE_TIMEOUT_SEC", "30"), default=30),
        memory_recall_limit=_read_int(source.get("MEMORY_RECALL_LIMIT", "10"), default=10),
        memory_decay_days=_read_int(source.get("MEMORY_DECAY_DAYS", "90"), default=90),
        learning_enabled=_read_bool(source.get("LEARNING_ENABLED", "true"), default=True),
        learning_min_signal_strength=_read_float(
            source.get("LEARNING_MIN_SIGNAL_STRENGTH", "0.6"),
            default=0.6,
        ),
        learning_correction_batch_size=_read_int(
            source.get("LEARNING_CORRECTION_BATCH_SIZE", "8"), default=8
        ),
        router_backend=source.get("ROUTER_BACKEND", "local"),
        router_model_path=Path(source.get("ROUTER_MODEL_PATH", "./experts/router.json")),
        router_confidence_threshold=_read_float(
            source.get("ROUTER_CONFIDENCE_THRESHOLD", "0.7"),
            default=0.7,
        ),
        router_daemon_cooldown_sec=_read_float(
            source.get("ROUTER_DAEMON_COOLDOWN_SEC", "5.0"),
            default=5.0,
        ),
        grpc_host=source.get("GRPC_HOST", "127.0.0.1"),
        grpc_port=_read_int(source.get("GRPC_PORT", "50051"), default=50051),
        grpc_timeout_sec=_read_float(source.get("GRPC_TIMEOUT_SEC", "0.5"), default=0.5),
        api_port=_read_int(source.get("API_PORT", "8080"), default=8080),
        log_level=source.get("LOG_LEVEL", "info"),
        max_citations=_read_int(source.get("MAX_CITATIONS", "4"), default=4),
        strict_runtime=_read_bool(source.get("STRICT_RUNTIME", "true"), default=True),
        action_audit_path=Path(
            source.get("ACTION_AUDIT_PATH", str(repo_root / "logs" / "assistant-actions.jsonl"))
        ),
        # Super Agent Settings
        super_agent_enabled=_read_bool(source.get("SUPER_AGENT_ENABLED", "true"), default=True),
        super_agent_reasoning_depth=source.get("SUPER_AGENT_REASONING_DEPTH", "deep"),
        super_agent_auto_approve_safe=_read_bool(source.get("SUPER_AGENT_AUTO_APPROVE_SAFE", "true"), default=True),
        super_agent_max_execution_time_sec=_read_float(source.get("SUPER_AGENT_MAX_EXECUTION_TIME_SEC", "60.0"), default=60.0),
        super_agent_learning_enabled=_read_bool(source.get("SUPER_AGENT_LEARNING_ENABLED", "true"), default=True),
        super_agent_safety_strict_mode=_read_bool(source.get("SUPER_AGENT_SAFETY_STRICT_MODE", "true"), default=True),
    )


def validate_settings(settings: BrainSettings) -> BrainSettings:
    """Validate settings and raise on error, otherwise return settings."""
    errors = settings.validate()
    if errors:
        raise ConfigValidationError(errors)
    return settings


def load_validated_settings(env: Mapping[str, str] | None = None) -> BrainSettings:
    """Load and validate settings, raising on validation errors."""
    return validate_settings(load_settings(env))
