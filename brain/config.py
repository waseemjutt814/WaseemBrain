from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


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
    whisper_model: str
    voice_sample_rate: int
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
    grpc_host: str
    grpc_port: int
    grpc_timeout_sec: float
    api_port: int
    log_level: str
    max_citations: int
    strict_runtime: bool


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
        http_user_agent=source.get("HTTP_USER_AGENT", "LatticeBrain/0.1"),
        http_allow_insecure_tls=_read_bool(
            source.get("HTTP_ALLOW_INSECURE_TLS", "false"),
            default=False,
        ),
        whisper_model=source.get("WHISPER_MODEL", "small"),
        voice_sample_rate=_read_int(source.get("VOICE_SAMPLE_RATE", "16000"), default=16000),
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
        router_backend=source.get("ROUTER_BACKEND", "auto"),
        router_model_path=Path(source.get("ROUTER_MODEL_PATH", "./experts/router.json")),
        router_confidence_threshold=_read_float(
            source.get("ROUTER_CONFIDENCE_THRESHOLD", "0.7"),
            default=0.7,
        ),
        grpc_host=source.get("GRPC_HOST", "127.0.0.1"),
        grpc_port=_read_int(source.get("GRPC_PORT", "50051"), default=50051),
        grpc_timeout_sec=_read_float(source.get("GRPC_TIMEOUT_SEC", "0.5"), default=0.5),
        api_port=_read_int(source.get("API_PORT", "8080"), default=8080),
        log_level=source.get("LOG_LEVEL", "info"),
        max_citations=_read_int(source.get("MAX_CITATIONS", "4"), default=4),
        strict_runtime=_read_bool(source.get("STRICT_RUNTIME", "true"), default=True),
    )
