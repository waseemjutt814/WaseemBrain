from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path

from brain.config import BrainSettings


def create_temp_dir() -> Path:
    """Create a Windows-safe temporary directory in the project folder."""
    # Use project tmp folder instead of system temp to avoid Windows path issues
    tmp_base = Path(__file__).resolve().parents[2] / "tmp"
    tmp_base.mkdir(exist_ok=True)
    # Create unique subfolder using timestamp
    temp_dir = tmp_base / f"test_{int(time.time() * 1000)}_{id(object())}"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


def make_settings(root: Path) -> BrainSettings:
    return BrainSettings(
        repo_root=root,
        expert_dir=root / "experts" / "base",
        expert_registry_path=root / "experts" / "registry.json",
        lora_dir=root / "experts" / "lora",
        chroma_dir=root / "data" / "vector",
        sqlite_dir=root / "data" / "sqlite",
        vector_index_path=root / "data" / "vector" / "memory.index",
        embedding_backend="hash",
        embedding_model_name="all-MiniLM-L6-v2",
        embedding_dimensions=384,
        memory_vector_backend="hnsw",
        learning_backend="offline",
        internet_enabled=True,
        internet_max_requests_per_query=5,
        internet_cache_ttl_seconds=3600,
        internet_allowed_domains=(),
        http_timeout_sec=10.0,
        http_user_agent="WaseemBrain-Test/0.1",
        http_allow_insecure_tls=False,
        assistant_mode="hybrid",
        model_provider="openai_compatible",
        model_base_url="",
        model_name="gpt-4o-mini",
        model_api_key="",
        whisper_model="base.en",
        voice_sample_rate=16000,
        voice_tts_enabled=True,
        expert_max_loaded=3,
        expert_idle_timeout_sec=1,
        memory_recall_limit=10,
        memory_decay_days=90,
        learning_enabled=True,
        learning_min_signal_strength=0.6,
        learning_correction_batch_size=8,
        router_backend="local",
        router_model_path=root / "experts" / "router.json",
        router_confidence_threshold=0.7,
        router_daemon_cooldown_sec=5.0,
        grpc_host="127.0.0.1",
        grpc_port=50051,
        grpc_timeout_sec=0.2,
        api_port=8080,
        log_level="info",
        max_citations=4,
        strict_runtime=True,
        action_audit_path=root / "logs" / "assistant-actions.jsonl",
        super_agent_enabled=True,
        super_agent_reasoning_depth="deep",
        super_agent_auto_approve_safe=True,
        super_agent_max_execution_time_sec=60.0,
        super_agent_learning_enabled=True,
        super_agent_safety_strict_mode=True,
    )


def seed_experts(settings: BrainSettings, with_policy: bool = False) -> None:
    settings.expert_dir.mkdir(parents=True, exist_ok=True)
    settings.lora_dir.mkdir(parents=True, exist_ok=True)
    registry = [
        {
            "id": "language-en",
            "name": "Language Expert",
            "domains": ["language", "writing", "general"],
            "kind": "grounded-language",
            "artifact_root": "language-en",
            "artifacts": [{"name": "manifest", "path": "manifest.json", "kind": "config"}],
            "capabilities": ["grounded-answering"],
            "load_strategy": "lazy",
            "description": "Evidence-backed synthesis",
        },
        {
            "id": "code-general",
            "name": "Code Expert",
            "domains": ["code", "python", "typescript", "rust"],
            "kind": "repo-code",
            "artifact_root": "code-general",
            "artifacts": [{"name": "manifest", "path": "manifest.json", "kind": "config"}],
            "capabilities": ["workspace-search"],
            "load_strategy": "lazy",
            "description": "Workspace search expert",
        },
        {
            "id": "geography",
            "name": "Geography Expert",
            "domains": ["geography", "countries"],
            "kind": "geography-dataset",
            "artifact_root": "geography",
            "artifacts": [
                {"name": "manifest", "path": "manifest.json", "kind": "config"},
                {"name": "countries", "path": "countries.json", "kind": "dataset"},
            ],
            "capabilities": ["capital-lookup"],
            "load_strategy": "lazy",
            "description": "Offline geography lookup",
        },
    ]
    settings.expert_registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    (settings.expert_dir / "language-en").mkdir(parents=True, exist_ok=True)
    (settings.expert_dir / "language-en" / "manifest.json").write_text(
        json.dumps({"kind": "grounded-language", "requires_evidence": True}, indent=2),
        encoding="utf-8",
    )
    (settings.expert_dir / "code-general").mkdir(parents=True, exist_ok=True)
    (settings.expert_dir / "code-general" / "manifest.json").write_text(
        json.dumps({"kind": "repo-code"}, indent=2),
        encoding="utf-8",
    )
    (settings.expert_dir / "geography").mkdir(parents=True, exist_ok=True)
    (settings.expert_dir / "geography" / "manifest.json").write_text(
        json.dumps({"kind": "geography-dataset", "dataset": "countries.json"}, indent=2),
        encoding="utf-8",
    )
    (settings.expert_dir / "geography" / "countries.json").write_text(
        json.dumps(
            [
                {"country": "France", "capital": "Paris", "region": "Europe"},
                {"country": "Pakistan", "capital": "Islamabad", "region": "Asia"},
                {"country": "Japan", "capital": "Tokyo", "region": "Asia"},
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    shutil.copyfile(Path(__file__).resolve().parents[2] / "experts" / "router.json", settings.router_model_path)
    if with_policy:
        policy_src = Path(__file__).resolve().parents[2] / "experts" / "response-policy.json"
        if policy_src.exists():
            shutil.copyfile(policy_src, settings.expert_dir.parent / "response-policy.json")
