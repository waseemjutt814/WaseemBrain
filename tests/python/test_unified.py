"""
Unified Test Suite for WaseemBrain
Combines all test modules into a single comprehensive test file.

File: tests/python/test_unified.py
Lines: 1-500+
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Setup environment
os.environ.setdefault("EMOTION_TEXT_BACKEND", "heuristic")
os.environ.setdefault("TEST_MODE", "true")

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import all modules under test
from brain.types import (
    EmbeddingVector,
    EmotionContext,
    EvidenceReference,
    ExpertId,
    ExpertOutput,
    MemoryNode,
    MemoryNodeId,
    NormalizedSignal,
    OkResult,
    Result,
    RouterDecision,
    SessionId,
    err,
    is_err,
    is_ok,
    ok,
)
from brain.config import BrainSettings, load_settings
from brain.dialogue import DialoguePlanner
from brain.memory.graph import MemoryGraph
from brain.experts.pool import ExpertPool
from brain.experts.registry import ExpertRegistry
from brain.router.client import ArtifactRouterClient, HybridRouterClient, RouterDaemonClient


# ============================================================================
# SECTION 1: TYPE TESTS (Lines 60-100)
# ============================================================================

class TestTypes:
    """Tests for brain/types.py - Core type definitions."""
    
    def test_ok_result_creation(self) -> None:
        """Test creating successful result."""
        result = ok("test_value")
        assert result["ok"] is True
        assert result["value"] == "test_value"
    
    def test_err_result_creation(self) -> None:
        """Test creating error result."""
        result = err("test_error")
        assert result["ok"] is False
        assert result["error"] == "test_error"
    
    def test_is_ok_typeguard(self) -> None:
        """Test is_ok typeguard function."""
        good_result: Result[str, str] = ok("success")
        bad_result: Result[str, str] = err("failure")
        assert is_ok(good_result) is True
        assert is_ok(bad_result) is False
    
    def test_is_err_typeguard(self) -> None:
        """Test is_err typeguard function."""
        good_result: Result[str, str] = ok("success")
        bad_result: Result[str, str] = err("failure")
        assert is_err(good_result) is False
        assert is_err(bad_result) is True
    
    def test_session_id_creation(self) -> None:
        """Test SessionId branded string."""
        sid = SessionId("test-session-123")
        assert str(sid) == "test-session-123"
        assert isinstance(sid, str)
    
    def test_expert_id_creation(self) -> None:
        """Test ExpertId branded string."""
        eid = ExpertId("code-expert")
        assert str(eid) == "code-expert"
    
    def test_memory_node_id_creation(self) -> None:
        """Test MemoryNodeId branded string."""
        nid = MemoryNodeId("mem-abc123")
        assert str(nid) == "mem-abc123"
    
    def test_embedding_vector_creation(self) -> None:
        """Test EmbeddingVector creation from iterable."""
        vec = EmbeddingVector([0.1, 0.2, 0.3, 0.4])
        assert len(vec) == 4
        assert vec[0] == pytest.approx(0.1)
    
    def test_embedding_vector_rejects_string(self) -> None:
        """Test that EmbeddingVector rejects string input."""
        with pytest.raises(TypeError):
            EmbeddingVector("not a vector")  # type: ignore


# ============================================================================
# SECTION 2: CONFIG TESTS (Lines 101-150)
# ============================================================================

class TestConfig:
    """Tests for brain/config.py - Configuration management."""
    
    def test_load_settings_defaults(self) -> None:
        """Test loading settings with default values."""
        settings = load_settings({})
        assert settings.embedding_backend == "auto"
        assert settings.embedding_dimensions == 384
        assert settings.internet_enabled is True
        assert settings.expert_max_loaded == 3
    
    def test_load_settings_from_env(self) -> None:
        """Test loading settings from environment."""
        env = {
            "EMBEDDING_BACKEND": "onnx",
            "EMBEDDING_DIMENSIONS": "512",
            "INTERNET_ENABLED": "false",
            "EXPERT_MAX_LOADED": "5",
        }
        settings = load_settings(env)
        assert settings.embedding_backend == "onnx"
        assert settings.embedding_dimensions == 512
        assert settings.internet_enabled is False
        assert settings.expert_max_loaded == 5
    
    def test_bool_parsing(self) -> None:
        """Test boolean value parsing."""
        from brain.config import _read_bool
        assert _read_bool("true", default=False) is True
        assert _read_bool("false", default=True) is False
        assert _read_bool("yes", default=False) is True
        assert _read_bool("no", default=True) is False
        assert _read_bool("invalid", default=True) is True
    
    def test_int_parsing(self) -> None:
        """Test integer value parsing."""
        from brain.config import _read_int
        assert _read_int("42", default=0) == 42
        assert _read_int("invalid", default=10) == 10
    
    def test_float_parsing(self) -> None:
        """Test float value parsing."""
        from brain.config import _read_float
        assert _read_float("3.14", default=0.0) == pytest.approx(3.14)
        assert _read_float("invalid", default=2.0) == pytest.approx(2.0)
    
    def test_settings_frozen(self) -> None:
        """Test that BrainSettings is immutable."""
        settings = load_settings({})
        with pytest.raises(AttributeError):
            settings.embedding_backend = "modified"  # type: ignore


# ============================================================================
# SECTION 3: DIALOGUE TESTS (Lines 151-220)
# ============================================================================

class TestDialogue:
    """Tests for brain/dialogue.py - Dialogue planning."""
    
    @pytest.fixture
    def planner(self) -> DialoguePlanner:
        """Create dialogue planner instance."""
        return DialoguePlanner()
    
    @pytest.fixture
    def sample_signal(self) -> NormalizedSignal:
        """Create sample normalized signal."""
        return {
            "text": "How do I fix the error in my Python code?",
            "modality": "text",
            "session_id": SessionId("test-session"),
        }
    
    @pytest.fixture
    def sample_emotion(self) -> EmotionContext:
        """Create sample emotion context."""
        return {
            "primary_emotion": "neutral",
            "valence": 0.5,
            "arousal": 0.3,
            "confidence": 0.8,
            "source": "text",
        }
    
    def test_build_state_code_intent(self, planner: DialoguePlanner) -> None:
        """Test dialogue state for code queries."""
        signal: NormalizedSignal = {"text": "Fix the bug in my function"}
        emotion: EmotionContext = {
            "primary_emotion": "neutral",
            "valence": 0.5,
            "arousal": 0.3,
            "confidence": 0.8,
            "source": "text",
        }
        state = planner.build_state(signal, emotion, [])
        assert state["intent"] == "code"
        assert "workspace" in state["signals"]
    
    def test_build_state_greeting(self, planner: DialoguePlanner) -> None:
        """Test dialogue state for greetings."""
        signal: NormalizedSignal = {"text": "Hi there"}
        emotion: EmotionContext = {
            "primary_emotion": "happy",
            "valence": 0.7,
            "arousal": 0.4,
            "confidence": 0.9,
            "source": "text",
        }
        state = planner.build_state(signal, emotion, [])
        assert state["intent"] == "greeting"
    
    def test_build_state_planning(self, planner: DialoguePlanner) -> None:
        """Test dialogue state for planning queries."""
        signal: NormalizedSignal = {"text": "What are the steps to implement this feature?"}
        emotion: EmotionContext = {
            "primary_emotion": "neutral",
            "valence": 0.5,
            "arousal": 0.3,
            "confidence": 0.8,
            "source": "text",
        }
        state = planner.build_state(signal, emotion, [])
        assert state["intent"] == "planning"
        assert state["prefers_steps"] is True
    
    def test_build_plan_clarify_mode(self, planner: DialoguePlanner) -> None:
        """Test response plan for ambiguous queries."""
        signal: NormalizedSignal = {"text": "fix it"}
        state = {
            "intent": "code",
            "style": "concise",
            "needs_clarification": True,
            "confidence": 0.3,
            "prefers_steps": False,
            "references_workspace": True,
            "references_memory": False,
            "asks_for_reasoning": False,
            "signals": ["clarify"],
            "locale": "en",
        }
        plan = planner.build_plan(
            signal,
            state,
            router_confidence=0.5,
            has_evidence=False,
            has_memory_answer=False,
        )
        assert plan["mode"] == "clarify"
    
    def test_build_plan_answer_mode(self, planner: DialoguePlanner) -> None:
        """Test response plan for clear queries."""
        signal: NormalizedSignal = {"text": "What is the capital of France?"}
        state = {
            "intent": "factual",
            "style": "concise",
            "needs_clarification": False,
            "confidence": 0.8,
            "prefers_steps": False,
            "references_workspace": False,
            "references_memory": False,
            "asks_for_reasoning": False,
            "signals": ["factual"],
            "locale": "en",
        }
        plan = planner.build_plan(
            signal,
            state,
            router_confidence=0.9,
            has_evidence=True,
            has_memory_answer=False,
        )
        assert plan["mode"] == "answer"
        assert plan["include_sources"] is True


# ============================================================================
# SECTION 4: MEMORY TESTS (Lines 221-300)
# ============================================================================

class TestMemory:
    """Tests for brain/memory/ - Memory graph and storage."""
    
    @pytest.fixture
    def settings(self, tmp_path: Path) -> BrainSettings:
        """Create test settings with temp directories."""
        return BrainSettings(
            repo_root=tmp_path,
            expert_dir=tmp_path / "experts",
            expert_registry_path=tmp_path / "registry.json",
            lora_dir=tmp_path / "lora",
            chroma_dir=tmp_path / "chroma",
            sqlite_dir=tmp_path / "sqlite",
            vector_index_path=tmp_path / "index.bin",
            embedding_backend="auto",
            embedding_model_name="test-model",
            embedding_dimensions=384,
            memory_vector_backend="hnsw",
            learning_backend="auto",
            internet_enabled=False,
            internet_max_requests_per_query=3,
            internet_cache_ttl_seconds=3600,
            internet_allowed_domains=(),
            http_timeout_sec=10.0,
            http_user_agent="Test/1.0",
            http_allow_insecure_tls=False,
            assistant_mode="hybrid",
            model_provider="openai_compatible",
            model_base_url="",
            model_name="gpt-4o-mini",
            model_api_key="",
            whisper_model="small",
            voice_sample_rate=16000,
            voice_tts_enabled=True,
            expert_max_loaded=2,
            expert_idle_timeout_sec=30,
            memory_recall_limit=10,
            memory_decay_days=90,
            learning_enabled=False,
            learning_min_signal_strength=0.6,
            learning_correction_batch_size=8,
            router_backend="auto",
            router_model_path=tmp_path / "router.json",
            router_confidence_threshold=0.7,
            router_daemon_cooldown_sec=5.0,
            grpc_host="127.0.0.1",
            grpc_port=50051,
            grpc_timeout_sec=0.5,
            api_port=8080,
            log_level="info",
            max_citations=4,
            strict_runtime=True,
            action_audit_path=tmp_path / "logs" / "assistant-actions.jsonl",
            super_agent_enabled=True,
            super_agent_reasoning_depth="deep",
            super_agent_auto_approve_safe=True,
            super_agent_max_execution_time_sec=60.0,
            super_agent_learning_enabled=True,
            super_agent_safety_strict_mode=True,
        )
    
    def test_memory_node_structure(self) -> None:
        """Test memory node typed dict structure."""
        node: MemoryNode = {
            "id": MemoryNodeId("mem-123"),
            "content": "Test content",
            "embedding": EmbeddingVector([0.1, 0.2, 0.3]),
            "tags": ["test"],
            "source": "test",
            "source_type": "memory",
            "created_at": time.time(),
            "last_accessed": time.time(),
            "access_count": 1,
            "confidence": 0.85,
            "session_id": SessionId("test"),
            "provenance": [],
        }
        assert node["id"] == "mem-123"
        assert node["confidence"] == 0.85


# ============================================================================
# SECTION 5: EXPERT TESTS (Lines 301-380)
# ============================================================================

class TestExperts:
    """Tests for brain/experts/ - Expert pool and registry."""
    
    def test_expert_id_validation(self) -> None:
        """Test ExpertId creation and validation."""
        eid = ExpertId("python-expert")
        assert str(eid) == "python-expert"
        assert isinstance(eid, str)
    
    def test_expert_output_structure(self) -> None:
        """Test ExpertOutput typed dict structure."""
        output: ExpertOutput = {
            "expert_id": ExpertId("test-expert"),
            "content": "Test response",
            "confidence": 0.9,
            "sources": ["source1"],
            "latency_ms": 150.0,
            "citations": [],
            "render_strategy": "grounded",
            "summary": "Test summary",
        }
        assert output["confidence"] == 0.9
        assert output["render_strategy"] == "grounded"


# ============================================================================
# SECTION 6: ROUTER TESTS (Lines 381-450)
# ============================================================================

class TestRouter:
    """Tests for brain/router/ - Router clients."""
    
    def test_router_decision_structure(self) -> None:
        """Test RouterDecision typed dict structure."""
        decision: RouterDecision = {
            "experts_needed": [ExpertId("code-expert")],
            "check_memory_first": True,
            "internet_needed": False,
            "confidence": 0.85,
            "reasoning_trace": "Code query detected",
        }
        assert decision["experts_needed"][0] == "code-expert"
        assert decision["check_memory_first"] is True
    
    def test_artifact_router_client_init(self) -> None:
        """Test ArtifactRouterClient initialization."""
        client = ArtifactRouterClient()
        assert client._artifact is None
    
    def test_router_daemon_client_init(self) -> None:
        """Test RouterDaemonClient initialization."""
        client = RouterDaemonClient("localhost:50051")
        assert client._target == "localhost:50051"
        assert client._timeout_sec == 0.5


# ============================================================================
# SECTION 7: INTEGRATION TESTS (Lines 451-500)
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_full_query_flow(self) -> None:
        """Test complete query processing flow."""
        # 1. Create signal
        signal: NormalizedSignal = {
            "text": "What is the error in my code?",
            "modality": "text",
            "session_id": SessionId("integration-test"),
        }
        
        # 2. Create emotion context
        emotion: EmotionContext = {
            "primary_emotion": "confused",
            "valence": 0.3,
            "arousal": 0.6,
            "confidence": 0.7,
            "source": "text",
        }
        
        # 3. Build dialogue state
        planner = DialoguePlanner()
        state = planner.build_state(signal, emotion, [])
        
        # 4. Verify state
        assert state["intent"] == "code"
        assert "workspace" in state["signals"]
        
        # 5. Build response plan
        plan = planner.build_plan(
            signal,
            state,
            router_confidence=0.8,
            has_evidence=True,
            has_memory_answer=False,
        )
        
        # 6. Verify plan
        assert plan["mode"] in ["answer", "clarify", "plan"]
    
    def test_error_handling_chain(self) -> None:
        """Test error propagation through result types."""
        # Create error result
        error = err("Test error message")
        
        # Verify error structure
        assert error["ok"] is False
        assert "Test error message" == error["error"]
        
        # Chain through functions
        def process_result(r: Result[str, str]) -> Result[int, str]:
            if is_ok(r):
                return ok(len(r["value"]))
            return r
        
        processed = process_result(error)
        assert is_err(processed)
        assert processed["error"] == "Test error message"


# ============================================================================
# SECTION 8: PERFORMANCE TESTS (Lines 501-550)
# ============================================================================

class TestPerformance:
    """Performance benchmarks for critical paths."""
    
    def test_embedding_vector_performance(self) -> None:
        """Test embedding vector creation performance."""
        import random
        values = [random.random() for _ in range(384)]
        
        start = time.perf_counter()
        for _ in range(1000):
            vec = EmbeddingVector(values)
        duration = time.perf_counter() - start
        
        # Should be fast (< 0.5s for 1000 iterations) - increased threshold for CI stability
        assert duration < 0.5, f"EmbeddingVector too slow: {duration}s"
    
    def test_result_creation_performance(self) -> None:
        """Test result creation performance."""
        start = time.perf_counter()
        for i in range(10000):
            result = ok(f"value_{i}")
        duration = time.perf_counter() - start
        
        # Should be very fast (< 0.05s for 10000 iterations)
        assert duration < 0.05, f"Result creation too slow: {duration}s"


# ============================================================================
# SECTION 9: EDGE CASE TESTS (Lines 551-600)
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_empty_string_handling(self) -> None:
        """Test handling of empty strings."""
        sid = SessionId("")
        assert str(sid) == ""
    
    def test_unicode_handling(self) -> None:
        """Test handling of unicode characters."""
        unicode_text = "Ã˜Â³Ã™â€žÃ˜Â§Ã™â€¦ Ã˜Â¯Ã™â€ Ã›Å’Ã˜Â§ Hello World Ã°Å¸Å’Â"
        signal: NormalizedSignal = {"text": unicode_text}
        assert signal["text"] == unicode_text
    
    def test_very_long_text(self) -> None:
        """Test handling of very long text."""
        long_text = "x" * 10000
        signal: NormalizedSignal = {"text": long_text}
        assert len(signal["text"]) == 10000
    
    def test_special_characters_in_query(self) -> None:
        """Test handling of special characters."""
        special_text = "SELECT * FROM users; DROP TABLE--"
        planner = DialoguePlanner()
        emotion: EmotionContext = {
            "primary_emotion": "neutral",
            "valence": 0.5,
            "arousal": 0.3,
            "confidence": 0.8,
            "source": "text",
        }
        state = planner.build_state({"text": special_text}, emotion, [])
        # Should not crash
        assert state is not None


# ============================================================================
# SECTION 10: FIXTURE TESTS (Lines 601-650)
# ============================================================================

@pytest.fixture
def mock_settings(tmp_path: Path) -> BrainSettings:
    """Fixture providing mock BrainSettings."""
    return BrainSettings(
            repo_root=tmp_path,
            expert_dir=tmp_path / "experts",
            expert_registry_path=tmp_path / "registry.json",
            lora_dir=tmp_path / "lora",
            chroma_dir=tmp_path / "chroma",
            sqlite_dir=tmp_path / "sqlite",
            vector_index_path=tmp_path / "index.bin",
            embedding_backend="auto",
            embedding_model_name="test-model",
            embedding_dimensions=384,
            memory_vector_backend="hnsw",
            learning_backend="auto",
            internet_enabled=False,
            internet_max_requests_per_query=3,
            internet_cache_ttl_seconds=3600,
            internet_allowed_domains=(),
            http_timeout_sec=10.0,
            http_user_agent="Test/1.0",
            http_allow_insecure_tls=False,
            assistant_mode="hybrid",
            model_provider="openai_compatible",
            model_base_url="",
            model_name="gpt-4o-mini",
            model_api_key="",
            whisper_model="small",
            voice_sample_rate=16000,
            voice_tts_enabled=True,
            expert_max_loaded=2,
            expert_idle_timeout_sec=30,
            memory_recall_limit=10,
            memory_decay_days=90,
            learning_enabled=False,
            learning_min_signal_strength=0.6,
            learning_correction_batch_size=8,
            router_backend="auto",
            router_model_path=tmp_path / "router.json",
            router_confidence_threshold=0.7,
            router_daemon_cooldown_sec=5.0,
            grpc_host="127.0.0.1",
            grpc_port=50051,
            grpc_timeout_sec=0.5,
            api_port=8080,
            log_level="info",
            max_citations=4,
            strict_runtime=True,
            action_audit_path=tmp_path / "logs" / "assistant-actions.jsonl",
            super_agent_enabled=True,
            super_agent_reasoning_depth="deep",
            super_agent_auto_approve_safe=True,
            super_agent_max_execution_time_sec=60.0,
            super_agent_learning_enabled=True,
            super_agent_safety_strict_mode=True,
        )


class TestWithFixtures:
    """Tests using pytest fixtures."""
    
    def test_with_mock_settings(self, mock_settings: BrainSettings) -> None:
        """Test using mock settings fixture."""
        assert mock_settings.internet_enabled is False
        assert mock_settings.expert_max_loaded == 2
    
    def test_tmp_path_fixture(self, tmp_path: Path) -> None:
        """Test tmp_path fixture."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        assert test_file.read_text() == "test content"


# ============================================================================
# TEST RUNNER CONFIGURATION
# ============================================================================

# Configure pytest
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config: Any) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short"])
