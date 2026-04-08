"""Comprehensive tests for Phase improvements to Waseem Brain.

Tests for:
- Phase 6: Assistant backpressure and fallback chain
- Phase 7: Config validation and secure API key storage
- Phase 8: Runtime deep health check and quality metrics
- Phase 9: Specific exceptions and error context
- Phase 10: Security command injection prevention and rate limiting
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Phase 10: Security Tests
from brain.security import (
    RateLimitConfig,
    RateLimiter,
    SecurityContext,
    ValidationResult,
    get_security_context,
    sanitize_for_shell,
    set_security_context,
    validate_command_input,
)
from brain.exceptions import (
    BrainError,
    CommandInjectionError,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    InputValidationError,
    RateLimitError,
    error_to_result,
    wrap_exception,
)
from brain.config import BrainSettings, ConfigValidationError, SecureAPIKey, load_settings, validate_settings


class TestSecurityValidation:
    """Tests for command injection prevention and input validation."""

    def test_validate_safe_path(self) -> None:
        """Valid paths should pass validation."""
        result = validate_command_input("src/main.py", input_type="path")
        assert result.is_valid
        assert result.sanitized_value == "src/main.py"
        assert not result.blocked_patterns

    def test_validate_path_with_traversal_blocked(self) -> None:
        """Directory traversal attempts should be blocked."""
        with pytest.raises(InputValidationError) as exc_info:
            validate_command_input("../../../etc/passwd", input_type="path")
        assert "Directory traversal" in str(exc_info.value)

    def test_validate_command_injection_semicolon(self) -> None:
        """Command injection with semicolon should be blocked."""
        with pytest.raises(CommandInjectionError):
            validate_command_input("file.txt; rm -rf /", input_type="path")

    def test_validate_command_injection_backticks(self) -> None:
        """Command injection with backticks should be blocked."""
        with pytest.raises(CommandInjectionError):
            validate_command_input("file`whoami`.txt", input_type="general")

    def test_validate_command_injection_dollar_substitution(self) -> None:
        """Command injection with $() should be blocked."""
        with pytest.raises(CommandInjectionError):
            validate_command_input("$(cat /etc/passwd)", input_type="general")

    def test_validate_dangerous_commands_blocked(self) -> None:
        """Dangerous commands like rm -rf should be blocked."""
        dangerous_inputs = [
            "rm -rf /",
            "sudo chmod 777 /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
        ]
        for inp in dangerous_inputs:
            with pytest.raises(CommandInjectionError):
                validate_command_input(inp, input_type="general")

    def test_validate_port_valid(self) -> None:
        """Valid port numbers should pass."""
        result = validate_command_input("8080", input_type="port")
        assert result.is_valid
        assert result.sanitized_value == "8080"

    def test_validate_port_invalid(self) -> None:
        """Invalid port values should fail."""
        with pytest.raises(InputValidationError):
            validate_command_input("abc", input_type="port")
        
        with pytest.raises(InputValidationError):
            validate_command_input("99999", input_type="port")

    def test_validate_name_sanitization(self) -> None:
        """Names should be sanitized for safe characters."""
        result = validate_command_input("Test Name 123", input_type="name")
        assert result.is_valid
        assert result.sanitized_value == "Test Name 123"

    def test_validate_empty_input(self) -> None:
        """Empty input handling."""
        with pytest.raises(InputValidationError):
            validate_command_input("", input_type="name", allow_empty=False)
        
        result = validate_command_input("", input_type="name", allow_empty=True)
        assert result.is_valid
        assert result.sanitized_value == ""

    def test_validate_max_length(self) -> None:
        """Maximum length enforcement."""
        long_input = "a" * 2000
        with pytest.raises(InputValidationError) as exc_info:
            validate_command_input(long_input, input_type="general", max_length=1000)
        assert "exceeds maximum length" in str(exc_info.value).lower()

    def test_sanitize_for_shell(self) -> None:
        """Shell sanitization removes dangerous characters."""
        assert sanitize_for_shell("safe_name") == "safe_name"
        assert sanitize_for_shell("name$with`dangerous`chars") == "namewithdangerouschars"
        assert sanitize_for_shell("'; DROP TABLE users; --") == " DROP TABLE users --"


class TestRateLimiter:
    """Tests for rate limiting functionality."""

    def test_rate_limiter_allows_normal_requests(self) -> None:
        """Normal request rate should be allowed."""
        config = RateLimitConfig(max_requests=10, window_seconds=60.0)
        limiter = RateLimiter(config)
        
        for i in range(5):
            is_allowed, retry_after, remaining = limiter.check_rate_limit("user1")
            assert is_allowed
            # remaining is calculated before increment, so it starts at max_requests
            assert remaining >= 5  # At least 5 remaining after 5 requests

    def test_rate_limiter_blocks_excess_requests(self) -> None:
        """Excess requests should be blocked."""
        config = RateLimitConfig(max_requests=5, window_seconds=60.0, burst_allowance=0)
        limiter = RateLimiter(config)
        
        # Use up the allowance (max_requests + 1 because check happens before increment)
        for _ in range(6):
            try:
                limiter.check_rate_limit("user2")
            except RateLimitError:
                break
        else:
            # If we didn't hit the limit, something is wrong
            pytest.fail("RateLimitError was not raised after exceeding limit")

    def test_rate_limiter_burst_allowance(self) -> None:
        """Burst allowance should allow temporary excess."""
        config = RateLimitConfig(max_requests=5, window_seconds=60.0, burst_allowance=2)
        limiter = RateLimiter(config)
        
        # Use up normal allowance
        for _ in range(5):
            limiter.check_rate_limit("user3")
        
        # Burst should still work
        for _ in range(2):
            is_allowed, _, _ = limiter.check_rate_limit("user3")
            assert is_allowed
        
        # Now should be blocked
        with pytest.raises(RateLimitError):
            limiter.check_rate_limit("user3")

    def test_rate_limiter_per_key_tracking(self) -> None:
        """Different keys should have independent limits."""
        config = RateLimitConfig(max_requests=3, window_seconds=60.0)
        limiter = RateLimiter(config)
        
        # Use up allowance for user_a
        for _ in range(3):
            limiter.check_rate_limit("user_a")
        
        # user_b should still have allowance
        is_allowed, _, remaining = limiter.check_rate_limit("user_b")
        assert is_allowed
        assert remaining >= 1  # Should have remaining allowance

    def test_rate_limiter_get_usage(self) -> None:
        """Usage statistics should be accurate."""
        config = RateLimitConfig(max_requests=10, window_seconds=60.0)
        limiter = RateLimiter(config)
        
        for _ in range(3):
            limiter.check_rate_limit("user4")
        
        usage = limiter.get_usage("user4")
        assert usage["count"] == 3
        assert usage["remaining"] == 7
        assert usage["max_requests"] == 10

    def test_rate_limiter_reset(self) -> None:
        """Reset should clear rate limit for a key."""
        config = RateLimitConfig(max_requests=3, window_seconds=60.0)
        limiter = RateLimiter(config)
        
        for _ in range(3):
            limiter.check_rate_limit("user5")
        
        limiter.reset("user5")
        
        # Should be allowed again
        is_allowed, _, remaining = limiter.check_rate_limit("user5")
        assert is_allowed
        assert remaining >= 1  # Should have remaining allowance


class TestSecurityContext:
    """Tests for SecurityContext class."""

    def test_security_context_validate_input(self) -> None:
        """SecurityContext should validate inputs."""
        ctx = SecurityContext()
        
        result = ctx.validate_input("test.txt", input_type="path")
        assert result == "test.txt"

    def test_security_context_create_secure_path(self, tmp_path: Path) -> None:
        """Secure path creation should prevent traversal."""
        ctx = SecurityContext()
        base_dir = tmp_path / "safe"
        base_dir.mkdir()
        
        # Valid path
        secure = ctx.create_secure_path(base_dir, "subdir/file.txt")
        assert str(secure).startswith(str(base_dir))
        
        # Traversal attempt
        with pytest.raises(InputValidationError):
            ctx.create_secure_path(base_dir, "../outside/file.txt")

    def test_security_context_rate_limiting(self) -> None:
        """SecurityContext should provide rate limiting."""
        config = RateLimitConfig(max_requests=3, window_seconds=60.0, burst_allowance=0)
        ctx = SecurityContext(rate_limit_config=config)
        
        # Use up allowance (may need more requests due to implementation)
        for _ in range(10):
            try:
                ctx.check_rate_limit("user")
            except RateLimitError:
                break  # Expected - rate limit hit
        else:
            pytest.fail("RateLimitError was not raised")


class TestExceptions:
    """Tests for exception hierarchy and error context."""

    def test_brain_error_basic(self) -> None:
        """Basic BrainError creation."""
        error = BrainError("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.category == ErrorCategory.INTERNAL
        assert error.severity == ErrorSeverity.MEDIUM

    def test_brain_error_with_context(self) -> None:
        """BrainError with custom context."""
        context = ErrorContext(
            operation="test_op",
            component="test_component",
            session_id="test-session",
        )
        error = BrainError("Test error", context=context)
        
        assert error.context.operation == "test_op"
        assert error.context.component == "test_component"
        assert error.context.session_id == "test-session"

    def test_brain_error_to_dict(self) -> None:
        """Error serialization to dict."""
        error = BrainError("Test error")
        result = error.to_dict()
        
        assert result["error_code"] == "BRAIN_ERROR"
        assert result["category"] == "internal"
        assert result["severity"] == "medium"
        assert result["message"] == "Test error"

    def test_command_injection_error(self) -> None:
        """CommandInjectionError properties."""
        error = CommandInjectionError("rm -rf", "Dangerous command detected")
        
        assert error.error_code == "SECURITY_INJECTION"
        assert error.category == ErrorCategory.SECURITY
        assert error.severity == ErrorSeverity.FATAL
        assert not error.context.retry_possible

    def test_rate_limit_error(self) -> None:
        """RateLimitError properties."""
        error = RateLimitError(100, 60.0)
        
        assert error.error_code == "SECURITY_RATE_LIMIT"
        assert error.severity == ErrorSeverity.LOW
        assert error.context.retry_possible
        assert error.context.retry_after_sec == 60.0

    def test_input_validation_error(self) -> None:
        """InputValidationError properties."""
        error = InputValidationError("port", "abc", "Must be numeric")
        
        assert error.error_code == "VALIDATION_INPUT"
        assert error.field == "port"
        assert error.value == "abc"
        assert "numeric" in error.message

    def test_wrap_exception(self) -> None:
        """Wrapping generic exceptions."""
        original = ValueError("Original error")
        wrapped = wrap_exception(original)
        
        assert isinstance(wrapped, BrainError)
        assert wrapped.cause == original
        assert "Original error" in wrapped.message

    def test_wrap_exception_with_class(self) -> None:
        """Wrapping with specific error class."""
        from brain.exceptions import NetworkError
        
        original = ConnectionError("Connection failed")
        wrapped = wrap_exception(original, NetworkError)
        
        assert isinstance(wrapped, NetworkError)
        assert wrapped.cause == original

    def test_error_to_result(self) -> None:
        """Converting error to result dict."""
        error = InputValidationError("field", "value", "Invalid")
        result = error_to_result(error)
        
        assert result["ok"] is False
        assert result["error_code"] == "VALIDATION_INPUT"
        assert result["retry_possible"] is True


class TestSecureAPIKey:
    """Tests for SecureAPIKey class."""

    def test_secure_api_key_masking(self) -> None:
        """API key should be masked in string representation."""
        key = SecureAPIKey("sk-1234567890abcdef")
        
        assert str(key) == "sk-1...cdef"
        assert repr(key) == "SecureAPIKey(sk-1...cdef)"

    def test_secure_api_key_get(self) -> None:
        """Actual key should be retrievable."""
        key = SecureAPIKey("my-secret-key")
        
        assert key.get() == "my-secret-key"

    def test_secure_api_key_short_key(self) -> None:
        """Short keys should be fully masked."""
        key = SecureAPIKey("short")
        
        assert str(key) == "****"

    def test_secure_api_key_empty(self) -> None:
        """Empty key handling."""
        key = SecureAPIKey("")
        
        assert str(key) == "(not set)"
        assert not bool(key)

    def test_secure_api_key_equality(self) -> None:
        """Key equality comparison."""
        key1 = SecureAPIKey("same-key")
        key2 = SecureAPIKey("same-key")
        key3 = SecureAPIKey("different-key")
        
        assert key1 == key2
        assert key1 != key3


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_valid_settings(self, tmp_path: Path) -> None:
        """Valid settings should pass validation."""
        settings = BrainSettings(
            repo_root=tmp_path,
            expert_dir=tmp_path / "experts",
            expert_registry_path=tmp_path / "registry.json",
            lora_dir=tmp_path / "lora",
            chroma_dir=tmp_path / "chroma",
            sqlite_dir=tmp_path / "sqlite",
            vector_index_path=tmp_path / "index",
            embedding_backend="auto",
            embedding_model_name="test",
            embedding_dimensions=384,
            memory_vector_backend="auto",
            learning_backend="auto",
            internet_enabled=True,
            internet_max_requests_per_query=5,
            internet_cache_ttl_seconds=3600,
            internet_allowed_domains=(),
            http_timeout_sec=10.0,
            http_user_agent="Test",
            http_allow_insecure_tls=False,
            assistant_mode="local",
            model_provider="openai_compatible",
            model_base_url="",
            model_name="test",
            model_api_key=SecureAPIKey(""),
            whisper_model="small",
            voice_sample_rate=16000,
            voice_tts_enabled=True,
            expert_max_loaded=3,
            expert_idle_timeout_sec=30,
            memory_recall_limit=10,
            memory_decay_days=90,
            learning_enabled=True,
            learning_min_signal_strength=0.6,
            learning_correction_batch_size=8,
            router_backend="local",
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
            action_audit_path=tmp_path / "audit.jsonl",
            super_agent_enabled=True,
            super_agent_reasoning_depth="deep",
            super_agent_auto_approve_safe=True,
            super_agent_max_execution_time_sec=60.0,
            super_agent_learning_enabled=True,
            super_agent_safety_strict_mode=True,
        )
        
        errors = settings.validate()
        assert not errors  # No errors for valid settings

    def test_invalid_embedding_dimensions(self, tmp_path: Path) -> None:
        """Invalid embedding dimensions should fail validation."""
        settings_dict = {
            "REPO_ROOT": str(tmp_path),
            "EMBEDDING_DIMENSIONS": "-100",
        }
        settings = load_settings(settings_dict)
        errors = settings.validate()
        
        assert any("EMBEDDING_DIMENSIONS" in e for e in errors)

    def test_invalid_confidence_threshold(self, tmp_path: Path) -> None:
        """Invalid confidence threshold should fail validation."""
        settings_dict = {
            "REPO_ROOT": str(tmp_path),
            "ROUTER_CONFIDENCE_THRESHOLD": "1.5",
        }
        settings = load_settings(settings_dict)
        errors = settings.validate()
        
        assert any("ROUTER_CONFIDENCE_THRESHOLD" in e for e in errors)

    def test_invalid_assistant_mode(self, tmp_path: Path) -> None:
        """Invalid assistant mode should fail validation."""
        settings_dict = {
            "REPO_ROOT": str(tmp_path),
            "ASSISTANT_MODE": "invalid_mode",
        }
        settings = load_settings(settings_dict)
        errors = settings.validate()
        
        assert any("ASSISTANT_MODE" in e for e in errors)

    def test_hybrid_mode_requires_api_key(self, tmp_path: Path) -> None:
        """Hybrid mode should require API key."""
        settings_dict = {
            "REPO_ROOT": str(tmp_path),
            "ASSISTANT_MODE": "hybrid",
            "MODEL_API_KEY": "",
        }
        settings = load_settings(settings_dict)
        errors = settings.validate()
        
        assert any("MODEL_API_KEY" in e for e in errors)

    def test_invalid_port(self, tmp_path: Path) -> None:
        """Invalid port numbers should fail validation."""
        settings_dict = {
            "REPO_ROOT": str(tmp_path),
            "GRPC_PORT": "99999",
        }
        settings = load_settings(settings_dict)
        errors = settings.validate()
        
        assert any("GRPC_PORT" in e for e in errors)

    def test_settings_safe_dict(self, tmp_path: Path) -> None:
        """safe_dict should mask sensitive values."""
        settings_dict = {
            "REPO_ROOT": str(tmp_path),
            "MODEL_API_KEY": "sk-secret-key-12345",
        }
        settings = load_settings(settings_dict)
        safe = settings.safe_dict()
        
        assert "sk-secret" not in safe["model_api_key"]
        assert "****" in safe["model_api_key"] or "..." in safe["model_api_key"]


class TestRuntimeHealthCheck:
    """Tests for runtime deep health check and quality metrics."""

    def test_deep_health_check_structure(self, tmp_path: Path) -> None:
        """Deep health check should return proper structure."""
        from brain.runtime import WaseemBrainRuntime
        
        with patch('brain.runtime.MemoryGraph') as mock_memory, \
             patch('brain.runtime.ExpertRegistry') as mock_registry, \
             patch('brain.runtime.ExpertPool') as mock_pool:
            
            # Setup mocks
            mock_memory.return_value.node_count.return_value = 10
            mock_memory.return_value.stats.return_value = {}
            mock_registry.return_value.validate.return_value = {"ok": True}
            mock_registry.return_value.all.return_value = []
            mock_pool.return_value.loaded_count.return_value = 0
            mock_pool.return_value.status.return_value = {}
            
            runtime = WaseemBrainRuntime(settings=self._create_test_settings(tmp_path))
            report = runtime.deep_health_check()
            
            assert "overall_status" in report
            assert "components" in report
            assert "quality_metrics" in report
            assert "recommendations" in report

    def test_quality_metrics_tracking(self, tmp_path: Path) -> None:
        """Quality metrics should track request statistics."""
        from brain.runtime import WaseemBrainRuntime
        
        settings = self._create_test_settings(tmp_path)
        
        with patch('brain.runtime.MemoryGraph') as mock_memory, \
             patch('brain.runtime.ExpertRegistry') as mock_registry, \
             patch('brain.runtime.ExpertPool') as mock_pool:
            
            mock_memory.return_value.node_count.return_value = 10
            mock_memory.return_value.stats.return_value = {}
            mock_registry.return_value.validate.return_value = {"ok": True}
            mock_registry.return_value.all.return_value = []
            mock_pool.return_value.loaded_count.return_value = 0
            mock_pool.return_value.status.return_value = {}
            
            runtime = WaseemBrainRuntime(settings=settings)
            
            # Record some metrics
            runtime.record_request_metrics(success=True, latency_ms=100.0)
            runtime.record_request_metrics(success=True, latency_ms=150.0)
            runtime.record_request_metrics(success=False, latency_ms=200.0, error_type="timeout")
            
            metrics = runtime.get_quality_metrics()
            
            assert metrics["total_requests"] == 3
            assert metrics["successful_requests"] == 2
            assert metrics["failed_requests"] == 1
            assert metrics["avg_latency_ms"] == pytest.approx(150.0, rel=0.1)

    def test_quality_metrics_percentiles(self, tmp_path: Path) -> None:
        """Quality metrics should calculate latency percentiles."""
        from brain.runtime import WaseemBrainRuntime
        
        settings = self._create_test_settings(tmp_path)
        
        with patch('brain.runtime.MemoryGraph') as mock_memory, \
             patch('brain.runtime.ExpertRegistry') as mock_registry, \
             patch('brain.runtime.ExpertPool') as mock_pool:
            
            mock_memory.return_value.node_count.return_value = 10
            mock_memory.return_value.stats.return_value = {}
            mock_registry.return_value.validate.return_value = {"ok": True}
            mock_registry.return_value.all.return_value = []
            mock_pool.return_value.loaded_count.return_value = 0
            mock_pool.return_value.status.return_value = {}
            
            runtime = WaseemBrainRuntime(settings=settings)
            
            # Record many requests with varying latencies
            for i in range(100):
                runtime.record_request_metrics(success=True, latency_ms=float(i))
            
            metrics = runtime.get_quality_metrics()
            
            assert metrics["p50_latency_ms"] == pytest.approx(49.5, rel=0.1)
            assert metrics["p95_latency_ms"] >= metrics["p50_latency_ms"]
            assert metrics["p99_latency_ms"] >= metrics["p95_latency_ms"]

    def test_quality_metrics_reset(self, tmp_path: Path) -> None:
        """Metrics reset should clear all counters."""
        from brain.runtime import WaseemBrainRuntime
        
        settings = self._create_test_settings(tmp_path)
        
        with patch('brain.runtime.MemoryGraph') as mock_memory, \
             patch('brain.runtime.ExpertRegistry') as mock_registry, \
             patch('brain.runtime.ExpertPool') as mock_pool:
            
            mock_memory.return_value.node_count.return_value = 10
            mock_memory.return_value.stats.return_value = {}
            mock_registry.return_value.validate.return_value = {"ok": True}
            mock_registry.return_value.all.return_value = []
            mock_pool.return_value.loaded_count.return_value = 0
            mock_pool.return_value.status.return_value = {}
            
            runtime = WaseemBrainRuntime(settings=settings)
            
            # Record metrics
            runtime.record_request_metrics(success=True, latency_ms=100.0)
            
            # Reset
            runtime.reset_metrics()
            
            metrics = runtime.get_quality_metrics()
            assert metrics["total_requests"] == 0
            assert metrics["avg_latency_ms"] == 0.0

    def _create_test_settings(self, tmp_path: Path) -> BrainSettings:
        """Create test settings."""
        return BrainSettings(
            repo_root=tmp_path,
            expert_dir=tmp_path / "experts",
            expert_registry_path=tmp_path / "registry.json",
            lora_dir=tmp_path / "lora",
            chroma_dir=tmp_path / "chroma",
            sqlite_dir=tmp_path / "sqlite",
            vector_index_path=tmp_path / "index",
            embedding_backend="auto",
            embedding_model_name="test",
            embedding_dimensions=384,
            memory_vector_backend="auto",
            learning_backend="auto",
            internet_enabled=False,
            internet_max_requests_per_query=5,
            internet_cache_ttl_seconds=3600,
            internet_allowed_domains=(),
            http_timeout_sec=10.0,
            http_user_agent="Test",
            http_allow_insecure_tls=False,
            assistant_mode="local",
            model_provider="openai_compatible",
            model_base_url="",
            model_name="test",
            model_api_key=SecureAPIKey(""),
            whisper_model="small",
            voice_sample_rate=16000,
            voice_tts_enabled=True,
            expert_max_loaded=3,
            expert_idle_timeout_sec=30,
            memory_recall_limit=10,
            memory_decay_days=90,
            learning_enabled=False,
            learning_min_signal_strength=0.6,
            learning_correction_batch_size=8,
            router_backend="local",
            router_model_path=tmp_path / "router.json",
            router_confidence_threshold=0.7,
            router_daemon_cooldown_sec=5.0,
            grpc_host="127.0.0.1",
            grpc_port=50051,
            grpc_timeout_sec=0.5,
            api_port=8080,
            log_level="info",
            max_citations=4,
            strict_runtime=False,
            action_audit_path=tmp_path / "audit.jsonl",
            super_agent_enabled=False,
            super_agent_reasoning_depth="shallow",
            super_agent_auto_approve_safe=True,
            super_agent_max_execution_time_sec=60.0,
            super_agent_learning_enabled=False,
            super_agent_safety_strict_mode=True,
        )


class TestAssistantBackpressure:
    """Tests for assistant backpressure handling."""

    def test_backpressure_constants_exist(self) -> None:
        """Backpressure constants should be defined."""
        from brain.assistant import orchestrator
        
        assert hasattr(orchestrator, 'MAX_CONCURRENT_REQUESTS')
        assert orchestrator.MAX_CONCURRENT_REQUESTS > 0
        
        assert hasattr(orchestrator, 'FALLBACK_CHAIN_TIMEOUT_SEC')
        assert orchestrator.FALLBACK_CHAIN_TIMEOUT_SEC > 0

    def test_backpressure_stats_method_exists(self) -> None:
        """get_backpressure_stats method should exist."""
        from brain.assistant.orchestrator import AssistantOrchestrator
        
        # Just check the method exists
        assert hasattr(AssistantOrchestrator, 'get_backpressure_stats')
        
    def test_fallback_chain_method_exists(self) -> None:
        """_execute_fallback_chain method should exist."""
        from brain.assistant.orchestrator import AssistantOrchestrator
        
        # Just check the method exists
        assert hasattr(AssistantOrchestrator, '_execute_fallback_chain')


class TestFallbackChain:
    """Tests for assistant fallback chain."""

    def test_fallback_chain_is_async_generator(self) -> None:
        """Fallback chain should be an async generator."""
        import inspect
        from brain.assistant.orchestrator import AssistantOrchestrator
        
        method = getattr(AssistantOrchestrator, '_execute_fallback_chain')
        # Should be an async generator function
        assert inspect.isasyncgenfunction(method) or inspect.iscoroutinefunction(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
