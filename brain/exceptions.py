"""Specific exceptions with error context for the Waseem Brain system.

This module provides a hierarchy of exceptions that carry rich context
for debugging, logging, and error handling throughout the system.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Severity level for errors."""
    LOW = "low"  # Minor issues, fallbacks available
    MEDIUM = "medium"  # Significant issues, degraded functionality
    HIGH = "high"  # Critical issues, core functionality affected
    FATAL = "fatal"  # System cannot continue


class ErrorCategory(Enum):
    """Category of error for classification."""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    STORAGE = "storage"
    MEMORY = "memory"
    EXPERT = "expert"
    ROUTER = "router"
    COORDINATOR = "coordinator"
    ASSISTANT = "assistant"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    SECURITY = "security"
    INTERNAL = "internal"


@dataclass
class ErrorContext:
    """Rich context for error debugging and logging."""
    timestamp: float = field(default_factory=time.time)
    operation: str = ""
    component: str = ""
    session_id: str | None = None
    request_id: str | None = None
    user_message: str | None = None
    technical_details: dict[str, Any] = field(default_factory=dict)
    stack_trace: str | None = None
    recovery_hint: str | None = None
    retry_possible: bool = True
    retry_after_sec: float | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "operation": self.operation,
            "component": self.component,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "user_message": self.user_message,
            "technical_details": self.technical_details,
            "recovery_hint": self.recovery_hint,
            "retry_possible": self.retry_possible,
            "retry_after_sec": self.retry_after_sec,
        }


class BrainError(Exception):
    """Base exception for all Waseem Brain errors.
    
    Provides structured error information with context, severity,
    and recovery hints.
    """
    
    error_code: str = "BRAIN_ERROR"
    category: ErrorCategory = ErrorCategory.INTERNAL
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    default_message: str = "An error occurred in the Waseem Brain system"
    
    def __init__(
        self,
        message: str | None = None,
        *,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
        **context_kwargs: Any,
    ) -> None:
        self.message = message or self.default_message
        self.context = context or ErrorContext(**context_kwargs)
        self.cause = cause
        super().__init__(self.message)
        
        # Set cause for exception chaining
        if cause is not None:
            self.__cause__ = cause
    
    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context.to_dict(),
            "cause": str(self.cause) if self.cause else None,
        }
    
    def user_facing_message(self) -> str:
        """Return a user-friendly error message."""
        if self.context.user_message:
            return self.context.user_message
        return self.message


# Configuration Errors
class ConfigurationError(BrainError):
    """Base for configuration-related errors."""
    error_code = "CONFIG_ERROR"
    category = ErrorCategory.CONFIGURATION
    default_message = "Configuration error"


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""
    error_code = "CONFIG_MISSING"
    severity = ErrorSeverity.HIGH
    
    def __init__(self, config_key: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Required configuration is missing. Please check settings.")
        kwargs.setdefault("recovery_hint", f"Set the {config_key} configuration value")
        super().__init__(f"Missing required configuration: {config_key}", **kwargs)
        self.config_key = config_key


class InvalidConfigurationError(ConfigurationError):
    """Configuration value is invalid."""
    error_code = "CONFIG_INVALID"
    severity = ErrorSeverity.HIGH
    
    def __init__(self, config_key: str, value: Any, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Invalid configuration value detected.")
        kwargs.setdefault("recovery_hint", f"Fix {config_key}: {reason}")
        super().__init__(f"Invalid configuration {config_key}={value}: {reason}", **kwargs)
        self.config_key = config_key
        self.value = value


# Network Errors
class NetworkError(BrainError):
    """Base for network-related errors."""
    error_code = "NETWORK_ERROR"
    category = ErrorCategory.NETWORK
    default_message = "Network error occurred"


class ConnectionError(NetworkError):
    """Failed to connect to a service."""
    error_code = "NETWORK_CONNECTION"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, endpoint: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Unable to connect to external service.")
        kwargs.setdefault("recovery_hint", f"Check connectivity to {endpoint}")
        kwargs.setdefault("retry_possible", True)
        kwargs.setdefault("retry_after_sec", 5.0)
        super().__init__(f"Failed to connect to {endpoint}", **kwargs)
        self.endpoint = endpoint


class TimeoutError(NetworkError):
    """Operation timed out."""
    error_code = "NETWORK_TIMEOUT"
    category = ErrorCategory.TIMEOUT
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, operation: str, timeout_sec: float, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Request timed out. Please try again.")
        kwargs.setdefault("retry_possible", True)
        kwargs.setdefault("retry_after_sec", min(timeout_sec, 10.0))
        super().__init__(f"Operation {operation} timed out after {timeout_sec}s", **kwargs)
        self.operation = operation
        self.timeout_sec = timeout_sec


class InternetQueryError(NetworkError):
    """Failed to query internet module."""
    error_code = "INTERNET_QUERY"
    severity = ErrorSeverity.LOW
    
    def __init__(self, query: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Unable to search for information. Using local knowledge.")
        kwargs.setdefault("retry_possible", True)
        super().__init__(f"Internet query failed for '{query}': {reason}", **kwargs)
        self.query = query


# Storage Errors
class StorageError(BrainError):
    """Base for storage-related errors."""
    error_code = "STORAGE_ERROR"
    category = ErrorCategory.STORAGE
    default_message = "Storage error occurred"


class DatabaseError(StorageError):
    """Database operation failed."""
    error_code = "STORAGE_DATABASE"
    severity = ErrorSeverity.HIGH
    
    def __init__(self, operation: str, table: str | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Database operation failed.")
        kwargs.setdefault("recovery_hint", "Check database connectivity and schema")
        super().__init__(f"Database operation '{operation}' failed on table {table}", **kwargs)
        self.operation = operation
        self.table = table


class VectorStoreError(StorageError):
    """Vector store operation failed."""
    error_code = "STORAGE_VECTOR"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, operation: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Memory search encountered an issue.")
        super().__init__(f"Vector store operation '{operation}' failed", **kwargs)
        self.operation = operation


# Memory Errors
class MemoryError(BrainError):
    """Base for memory-related errors."""
    error_code = "MEMORY_ERROR"
    category = ErrorCategory.MEMORY
    default_message = "Memory operation error"


class MemoryStoreError(MemoryError):
    """Failed to store memory node."""
    error_code = "MEMORY_STORE"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, content_preview: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Failed to save information to memory.")
        super().__init__(f"Failed to store memory: {reason} (content: {content_preview[:50]}...)", **kwargs)


class MemoryRecallError(MemoryError):
    """Failed to recall from memory."""
    error_code = "MEMORY_RECALL"
    severity = ErrorSeverity.LOW
    
    def __init__(self, query: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Unable to search memory effectively.")
        kwargs.setdefault("retry_possible", True)
        super().__init__(f"Memory recall failed for '{query}': {reason}", **kwargs)


class EmbeddingError(MemoryError):
    """Failed to generate embedding."""
    error_code = "MEMORY_EMBEDDING"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, text_preview: str, backend: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Failed to process text for semantic search.")
        kwargs.setdefault("recovery_hint", f"Check {backend} embedding backend")
        super().__init__(f"Embedding failed with {backend} backend: {text_preview[:50]}...", **kwargs)


# Expert Errors
class ExpertError(BrainError):
    """Base for expert-related errors."""
    error_code = "EXPERT_ERROR"
    category = ErrorCategory.EXPERT
    default_message = "Expert operation error"


class ExpertLoadError(ExpertError):
    """Failed to load expert."""
    error_code = "EXPERT_LOAD"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, expert_id: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Unable to load specialized component.")
        kwargs.setdefault("recovery_hint", f"Check expert {expert_id} configuration")
        super().__init__(f"Failed to load expert {expert_id}: {reason}", **kwargs)
        self.expert_id = expert_id


class ExpertInferenceError(ExpertError):
    """Expert inference failed."""
    error_code = "EXPERT_INFERENCE"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, expert_id: str, query: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Processing encountered an issue.")
        kwargs.setdefault("retry_possible", True)
        super().__init__(f"Expert {expert_id} inference failed on '{query[:30]}...': {reason}", **kwargs)
        self.expert_id = expert_id


class ExpertPoolError(ExpertError):
    """Expert pool operation failed."""
    error_code = "EXPERT_POOL"
    severity = ErrorSeverity.HIGH
    
    def __init__(self, operation: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Expert system encountered an error.")
        super().__init__(f"Expert pool operation '{operation}' failed: {reason}", **kwargs)


# Router Errors
class RouterError(BrainError):
    """Base for router-related errors."""
    error_code = "ROUTER_ERROR"
    category = ErrorCategory.ROUTER
    default_message = "Router operation error"


class RouterDecisionError(RouterError):
    """Router failed to make a decision."""
    error_code = "ROUTER_DECISION"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, query: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Unable to determine best processing path.")
        kwargs.setdefault("retry_possible", True)
        super().__init__(f"Router decision failed for '{query[:30]}...': {reason}", **kwargs)


class RouterDaemonError(RouterError):
    """Router daemon communication failed."""
    error_code = "ROUTER_DAEMON"
    severity = ErrorSeverity.LOW
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Using fallback routing mode.")
        kwargs.setdefault("recovery_hint", "Router daemon unavailable, using local artifact")
        super().__init__(f"Router daemon error: {reason}", **kwargs)


# Coordinator Errors
class CoordinatorError(BrainError):
    """Base for coordinator-related errors."""
    error_code = "COORDINATOR_ERROR"
    category = ErrorCategory.COORDINATOR
    default_message = "Coordinator operation error"


class CoordinatorTimeoutError(CoordinatorError):
    """Coordinator processing timed out."""
    error_code = "COORDINATOR_TIMEOUT"
    category = ErrorCategory.TIMEOUT
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, stage: str, timeout_sec: float, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Processing took too long. Please try again.")
        kwargs.setdefault("retry_possible", True)
        kwargs.setdefault("retry_after_sec", min(timeout_sec, 30.0))
        super().__init__(f"Coordinator timed out after {timeout_sec}s during {stage}", **kwargs)
        self.stage = stage
        self.timeout_sec = timeout_sec


class CoordinatorProcessingError(CoordinatorError):
    """Coordinator processing failed."""
    error_code = "COORDINATOR_PROCESSING"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, stage: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Processing encountered an error.")
        kwargs.setdefault("retry_possible", True)
        super().__init__(f"Coordinator processing failed at {stage}: {reason}", **kwargs)
        self.stage = stage


# Assistant Errors
class AssistantError(BrainError):
    """Base for assistant-related errors."""
    error_code = "ASSISTANT_ERROR"
    category = ErrorCategory.ASSISTANT
    default_message = "Assistant operation error"


class AssistantBackpressureError(AssistantError):
    """Too many concurrent requests."""
    error_code = "ASSISTANT_BACKPRESSURE"
    category = ErrorCategory.RESOURCE
    severity = ErrorSeverity.LOW
    
    def __init__(self, active_requests: int, max_requests: int, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Server is busy. Please try again in a moment.")
        kwargs.setdefault("retry_possible", True)
        kwargs.setdefault("retry_after_sec", 5.0)
        super().__init__(f"Backpressure: {active_requests}/{max_requests} requests active", **kwargs)
        self.active_requests = active_requests
        self.max_requests = max_requests


class AssistantTimeoutError(AssistantError):
    """Assistant processing timed out."""
    error_code = "ASSISTANT_TIMEOUT"
    category = ErrorCategory.TIMEOUT
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, timeout_sec: float, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Request took too long. Please try again.")
        kwargs.setdefault("retry_possible", True)
        super().__init__(f"Assistant timed out after {timeout_sec}s", **kwargs)


class ProviderError(AssistantError):
    """External provider error."""
    error_code = "ASSISTANT_PROVIDER"
    category = ErrorCategory.NETWORK
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, provider: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "External AI service unavailable. Using local mode.")
        kwargs.setdefault("recovery_hint", f"Check {provider} provider configuration and connectivity")
        super().__init__(f"Provider {provider} error: {reason}", **kwargs)
        self.provider = provider


# Validation Errors
class ValidationError(BrainError):
    """Base for validation errors."""
    error_code = "VALIDATION_ERROR"
    category = ErrorCategory.VALIDATION
    default_message = "Validation error"


class InputValidationError(ValidationError):
    """Input validation failed."""
    error_code = "VALIDATION_INPUT"
    severity = ErrorSeverity.LOW
    
    def __init__(self, field: str, value: Any, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", f"Invalid input: {reason}")
        kwargs.setdefault("retry_possible", True)
        super().__init__(f"Validation failed for {field}={value}: {reason}", **kwargs)
        self.field = field
        self.value = value


class SchemaValidationError(ValidationError):
    """Schema validation failed."""
    error_code = "VALIDATION_SCHEMA"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, schema: str, errors: list[str], **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Data format error detected.")
        super().__init__(f"Schema validation failed for {schema}: {'; '.join(errors)}", **kwargs)
        self.schema = schema
        self.errors = errors


# Resource Errors
class ResourceError(BrainError):
    """Base for resource-related errors."""
    error_code = "RESOURCE_ERROR"
    category = ErrorCategory.RESOURCE
    default_message = "Resource error"


class ResourceExhaustedError(ResourceError):
    """Resource limit exceeded."""
    error_code = "RESOURCE_EXHAUSTED"
    severity = ErrorSeverity.HIGH
    
    def __init__(self, resource: str, limit: int, current: int, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "System resource limit reached. Please try again later.")
        kwargs.setdefault("retry_possible", True)
        kwargs.setdefault("retry_after_sec", 30.0)
        super().__init__(f"Resource {resource} exhausted: {current}/{limit}", **kwargs)
        self.resource = resource
        self.limit = limit
        self.current = current


class ConnectionPoolExhaustedError(ResourceError):
    """Connection pool exhausted."""
    error_code = "RESOURCE_POOL"
    severity = ErrorSeverity.MEDIUM
    
    def __init__(self, pool_name: str, pool_size: int, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Connection limit reached. Please retry.")
        kwargs.setdefault("retry_possible", True)
        kwargs.setdefault("retry_after_sec", 5.0)
        super().__init__(f"Connection pool {pool_name} exhausted (size: {pool_size})", **kwargs)


# Security Errors
class SecurityError(BrainError):
    """Base for security-related errors."""
    error_code = "SECURITY_ERROR"
    category = ErrorCategory.SECURITY
    severity = ErrorSeverity.HIGH
    default_message = "Security error"


class CommandInjectionError(SecurityError):
    """Potential command injection detected."""
    error_code = "SECURITY_INJECTION"
    severity = ErrorSeverity.FATAL
    
    def __init__(self, command: str, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Invalid command detected for security reasons.")
        kwargs.setdefault("retry_possible", False)
        super().__init__(f"Command injection detected: {reason} (command: {command[:30]}...)", **kwargs)


class RateLimitError(SecurityError):
    """Rate limit exceeded."""
    error_code = "SECURITY_RATE_LIMIT"
    severity = ErrorSeverity.LOW
    
    def __init__(self, limit: int, window_sec: float, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Too many requests. Please wait before trying again.")
        kwargs.setdefault("retry_possible", True)
        kwargs.setdefault("retry_after_sec", window_sec)
        super().__init__(f"Rate limit exceeded: {limit} requests per {window_sec}s", **kwargs)


class AuthenticationError(SecurityError):
    """Authentication failed."""
    error_code = "SECURITY_AUTH"
    severity = ErrorSeverity.HIGH
    
    def __init__(self, reason: str, **kwargs: Any) -> None:
        kwargs.setdefault("user_message", "Authentication failed.")
        kwargs.setdefault("retry_possible", False)
        super().__init__(f"Authentication error: {reason}", **kwargs)


# Helper functions
def wrap_exception(
    exc: Exception,
    error_class: type[BrainError] | None = None,
    **context_kwargs: Any,
) -> BrainError:
    """Wrap a generic exception into a BrainError.
    
    Args:
        exc: The original exception
        error_class: The BrainError subclass to use (defaults to BrainError)
        **context_kwargs: Additional context for the error
        
    Returns:
        A BrainError wrapping the original exception
    """
    if isinstance(exc, BrainError):
        return exc
    
    error_cls = error_class or BrainError
    return error_cls(
        str(exc),
        cause=exc,
        **context_kwargs,
    )


def error_to_result(error: BrainError) -> dict[str, Any]:
    """Convert a BrainError to a Result-style dictionary.
    
    Args:
        error: The BrainError to convert
        
    Returns:
        An error result dictionary
    """
    return {
        "ok": False,
        "error": error.message,
        "error_code": error.error_code,
        "error_category": error.category.value,
        "error_severity": error.severity.value,
        "context": error.context.to_dict(),
        "retry_possible": error.context.retry_possible,
        "retry_after_sec": error.context.retry_after_sec,
    }


__all__ = [
    "ErrorCategory",
    "ErrorContext",
    "ErrorSeverity",
    "BrainError",
    # Configuration
    "ConfigurationError",
    "MissingConfigurationError",
    "InvalidConfigurationError",
    # Network
    "NetworkError",
    "ConnectionError",
    "TimeoutError",
    "InternetQueryError",
    # Storage
    "StorageError",
    "DatabaseError",
    "VectorStoreError",
    # Memory
    "MemoryError",
    "MemoryStoreError",
    "MemoryRecallError",
    "EmbeddingError",
    # Expert
    "ExpertError",
    "ExpertLoadError",
    "ExpertInferenceError",
    "ExpertPoolError",
    # Router
    "RouterError",
    "RouterDecisionError",
    "RouterDaemonError",
    # Coordinator
    "CoordinatorError",
    "CoordinatorTimeoutError",
    "CoordinatorProcessingError",
    # Assistant
    "AssistantError",
    "AssistantBackpressureError",
    "AssistantTimeoutError",
    "ProviderError",
    # Validation
    "ValidationError",
    "InputValidationError",
    "SchemaValidationError",
    # Resource
    "ResourceError",
    "ResourceExhaustedError",
    "ConnectionPoolExhaustedError",
    # Security
    "SecurityError",
    "CommandInjectionError",
    "RateLimitError",
    "AuthenticationError",
    # Helpers
    "wrap_exception",
    "error_to_result",
]
