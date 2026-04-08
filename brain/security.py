"""Security utilities for command injection prevention and rate limiting.

This module provides security measures to protect the Waseem Brain system
from malicious inputs and resource abuse.
"""
from __future__ import annotations

import hashlib
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Literal

from .exceptions import CommandInjectionError, RateLimitError, InputValidationError


# Dangerous command patterns that should be blocked
DANGEROUS_PATTERNS = [
    # Command chaining
    r'[;&|`]',  # ; & | `
    r'\$\([^)]*\)',  # $(command)
    r'`[^`]*`',  # `command`
    r'\$\{[^}]*\}',  # ${variable}
    r'\$\[[^]]*\]',  # ${command}
    
    # Redirection attacks
    r'>\s*/',  # Redirect to root
    r'>\s*~',  # Redirect to home
    r'>\s*\.\.',  # Directory traversal
    
    # Shell expansion
    r'\*',  # Wildcard
    r'\?',  # Single char wildcard
    r'\[',  # Character class
    r'\{',  # Brace expansion
    
    # Environment manipulation
    r'env\s+-i',  # Clear environment
    r'setenv',  # Set environment
    r'export\s+\w+=',  # Export variable
    
    # Privilege escalation
    r'sudo',  # sudo
    r'su\s',  # su command
    r'chmod\s+[0-7]*777',  # chmod 777
    r'chown\s+root',  # chown root
    
    # Dangerous commands
    r'\brm\s+-rf\b',  # rm -rf
    r'\bdd\s+',  # dd command
    r'\bmkfs\b',  # Format filesystem
    r'\bfdisk\b',  # Partition tool
    r'\bshutdown\b',  # Shutdown
    r'\breboot\b',  # Reboot
    r'\binit\s+[06]',  # Init to different runlevel
    
    # Network attacks
    r'\bnc\s+',  # netcat
    r'\bncat\s+',  # ncat
    r'\bnetcat\s+',  # netcat
    r'\btelnet\s+',  # telnet
    r'\bwget\s+',  # wget
    r'\bcurl\s+',  # curl (when used maliciously)
    
    # Script injection
    r'<script',  # HTML script tag
    r'javascript:',  # JavaScript protocol
    r'onerror\s*=',  # Event handler
    r'onload\s*=',  # Event handler
]

# Compile patterns for efficiency
_COMPILED_DANGEROUS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]

# Allowed characters for various input types
SAFE_PATH_CHARS = re.compile(r'^[a-zA-Z0-9_\-./\\]+$')
SAFE_NAME_CHARS = re.compile(r'^[a-zA-Z0-9_\- ]+$')
SAFE_PORT_CHARS = re.compile(r'^[0-9]+$')


@dataclass
class ValidationResult:
    """Result of security validation."""
    is_valid: bool
    sanitized_value: str
    warnings: list[str] = field(default_factory=list)
    blocked_patterns: list[str] = field(default_factory=list)


def validate_command_input(
    value: str,
    *,
    input_type: Literal["path", "name", "port", "pattern", "general"] = "general",
    max_length: int = 1000,
    allow_empty: bool = False,
) -> ValidationResult:
    """Validate and sanitize input for command execution.
    
    Args:
        value: The input value to validate
        input_type: Type of input for context-specific validation
        max_length: Maximum allowed length
        allow_empty: Whether empty values are allowed
        
    Returns:
        ValidationResult with sanitized value and any warnings/blocked patterns
        
    Raises:
        CommandInjectionError: If dangerous patterns are detected
        InputValidationError: If input fails validation
    """
    warnings: list[str] = []
    blocked_patterns: list[str] = []
    
    # Check empty
    if not value or not value.strip():
        if allow_empty:
            return ValidationResult(True, "", [], [])
        raise InputValidationError(
            "input",
            value,
            "Input cannot be empty",
            user_message="This field cannot be empty.",
        )
    
    # Check length
    if len(value) > max_length:
        raise InputValidationError(
            "input",
            value[:50],
            f"Input exceeds maximum length of {max_length}",
            user_message=f"Input is too long (max {max_length} characters).",
        )
    
    # Check for dangerous patterns
    for pattern in _COMPILED_DANGEROUS:
        match = pattern.search(value)
        if match:
            blocked_patterns.append(match.group())
    
    if blocked_patterns:
        raise CommandInjectionError(
            value[:50],
            f"Blocked patterns detected: {', '.join(blocked_patterns[:3])}",
            context={"blocked_patterns": blocked_patterns},
        )
    
    # Type-specific validation
    if input_type == "path":
        if not SAFE_PATH_CHARS.match(value):
            # Try to sanitize
            sanitized = ''.join(c for c in value if SAFE_PATH_CHARS.match(c))
            if sanitized != value:
                warnings.append("Some characters were removed from the path")
            value = sanitized
        # Normalize path
        try:
            path = Path(value)
            # Check for directory traversal
            if '..' in str(path) or str(path).startswith('/') or str(path).startswith('\\'):
                raise InputValidationError(
                    "path",
                    value,
                    "Directory traversal detected",
                    user_message="Invalid path: directory traversal not allowed.",
                )
        except Exception as exc:
            if isinstance(exc, InputValidationError):
                raise
            warnings.append(f"Path normalization warning: {exc}")
    
    elif input_type == "name":
        if not SAFE_NAME_CHARS.match(value):
            sanitized = ''.join(c for c in value if SAFE_NAME_CHARS.match(c))
            if sanitized != value:
                warnings.append("Some characters were removed from the name")
            value = sanitized
    
    elif input_type == "port":
        if not SAFE_PORT_CHARS.match(value):
            raise InputValidationError(
                "port",
                value,
                "Port must be numeric",
                user_message="Port must be a number.",
            )
        port_num = int(value)
        if port_num < 1 or port_num > 65535:
            raise InputValidationError(
                "port",
                value,
                f"Port {port_num} out of valid range (1-65535)",
                user_message="Port must be between 1 and 65535.",
            )
    
    elif input_type == "pattern":
        # For search patterns, allow more characters but still block dangerous ones
        # Already checked for dangerous patterns above
        pass
    
    else:  # general
        # General sanitization - remove control characters
        value = ''.join(c for c in value if ord(c) >= 32 or c in '\n\r\t')
    
    return ValidationResult(True, value, warnings, [])


def sanitize_for_shell(value: str) -> str:
    """Sanitize a value for safe shell usage.
    
    This is a defense-in-depth measure. Inputs should be validated
    before reaching this point.
    
    Args:
        value: The value to sanitize
        
    Returns:
        Sanitized value safe for shell usage
    """
    # Remove any shell metacharacters
    dangerous = ['$', '`', '"', "'", '\\', '\n', '\r', ';', '&', '|', '(', ')', '<', '>']
    result = value
    for char in dangerous:
        result = result.replace(char, '')
    
    # Limit to alphanumeric and safe punctuation
    result = ''.join(c for c in result if c.isalnum() or c in '._-/\\:@ ')
    
    return result


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 100
    window_seconds: float = 60.0
    burst_allowance: int = 10  # Extra requests allowed in burst
    
    @property
    def requests_per_second(self) -> float:
        return self.max_requests / self.window_seconds


@dataclass
class RateLimitEntry:
    """Entry tracking rate limit usage."""
    count: int = 0
    burst_count: int = 0
    window_start: float = 0.0
    last_request: float = 0.0
    blocked_count: int = 0


class RateLimiter:
    """Thread-safe rate limiter with sliding window and burst support.
    
    Supports multiple rate limit keys (e.g., per-user, per-IP, global).
    """
    
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = Lock()
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._last_cleanup = time.time()
    
    def check_rate_limit(
        self,
        key: str,
        *,
        increment: bool = True,
    ) -> tuple[bool, float, int]:
        """Check if a request is within rate limits.
        
        Args:
            key: The rate limit key (e.g., user ID, IP address)
            increment: Whether to increment the counter
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds, remaining_requests)
            
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        with self._lock:
            now = time.time()
            entry = self._entries[key]
            
            # Check if window has expired
            if now - entry.window_start > self._config.window_seconds:
                # Reset window
                entry.count = 0
                entry.burst_count = 0
                entry.window_start = now
            
            # Calculate remaining
            remaining = max(0, self._config.max_requests - entry.count)
            burst_remaining = max(0, self._config.burst_allowance - entry.burst_count)
            
            # Check if within limits
            is_allowed = entry.count < self._config.max_requests
            
            # Check burst allowance if over normal limit
            if not is_allowed and entry.burst_count < self._config.burst_allowance:
                is_allowed = True
                if increment:
                    entry.burst_count += 1
            elif is_allowed and increment:
                entry.count += 1
            
            if increment:
                entry.last_request = now
            
            if not is_allowed:
                entry.blocked_count += 1
                retry_after = self._config.window_seconds - (now - entry.window_start)
                raise RateLimitError(
                    self._config.max_requests,
                    self._config.window_seconds,
                    context={
                        "key": key,
                        "current_count": entry.count,
                        "retry_after_sec": retry_after,
                    },
                )
            
            # Periodic cleanup
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired(now)
            
            return is_allowed, 0.0, remaining
    
    def get_usage(self, key: str) -> dict[str, Any]:
        """Get current usage statistics for a key."""
        with self._lock:
            now = time.time()
            entry = self._entries.get(key)
            
            if entry is None:
                return {
                    "count": 0,
                    "max_requests": self._config.max_requests,
                    "remaining": self._config.max_requests,
                    "window_seconds": self._config.window_seconds,
                    "window_remaining": self._config.window_seconds,
                }
            
            window_remaining = max(0, self._config.window_seconds - (now - entry.window_start))
            remaining = max(0, self._config.max_requests - entry.count)
            
            return {
                "count": entry.count,
                "burst_count": entry.burst_count,
                "max_requests": self._config.max_requests,
                "burst_allowance": self._config.burst_allowance,
                "remaining": remaining,
                "window_seconds": self._config.window_seconds,
                "window_remaining": window_remaining,
                "blocked_count": entry.blocked_count,
            }
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key."""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
    
    def reset_all(self) -> None:
        """Reset all rate limits."""
        with self._lock:
            self._entries.clear()
    
    def _cleanup_expired(self, now: float) -> None:
        """Remove expired entries to prevent memory growth."""
        expired_keys = [
            key for key, entry in self._entries.items()
            if now - entry.last_request > self._config.window_seconds * 2
        ]
        for key in expired_keys:
            del self._entries[key]
        self._last_cleanup = now


class SecurityContext:
    """Security context for request processing.
    
    Provides centralized security validation and rate limiting.
    """
    
    def __init__(
        self,
        rate_limit_config: RateLimitConfig | None = None,
        strict_mode: bool = True,
    ) -> None:
        self._rate_limiter = RateLimiter(rate_limit_config)
        self._strict_mode = strict_mode
        self._validation_cache: dict[str, ValidationResult] = {}
        self._cache_lock = Lock()
    
    def validate_input(
        self,
        value: str,
        *,
        input_type: Literal["path", "name", "port", "pattern", "general"] = "general",
        max_length: int = 1000,
        allow_empty: bool = False,
        cache_key: str | None = None,
    ) -> str:
        """Validate input with optional caching.
        
        Args:
            value: Input to validate
            input_type: Type of input
            max_length: Maximum length
            allow_empty: Allow empty values
            cache_key: Optional cache key for repeated validations
            
        Returns:
            Sanitized value
        """
        # Check cache
        if cache_key:
            with self._cache_lock:
                cached = self._validation_cache.get(cache_key)
                if cached and cached.sanitized_value == value:
                    return value
        
        # Validate
        result = validate_command_input(
            value,
            input_type=input_type,
            max_length=max_length,
            allow_empty=allow_empty,
        )
        
        # Cache result
        if cache_key:
            with self._cache_lock:
                self._validation_cache[cache_key] = result
                # Limit cache size
                if len(self._validation_cache) > 1000:
                    # Remove oldest half
                    keys = list(self._validation_cache.keys())[:500]
                    for k in keys:
                        del self._validation_cache[k]
        
        return result.sanitized_value
    
    def check_rate_limit(
        self,
        key: str,
        *,
        increment: bool = True,
    ) -> tuple[bool, float, int]:
        """Check rate limit for a key."""
        return self._rate_limiter.check_rate_limit(key, increment=increment)
    
    def get_rate_limit_usage(self, key: str) -> dict[str, Any]:
        """Get rate limit usage for a key."""
        return self._rate_limiter.get_usage(key)
    
    def create_secure_path(self, base_dir: Path, relative_path: str) -> Path:
        """Create a secure path within a base directory.
        
        Ensures the resulting path stays within base_dir.
        
        Args:
            base_dir: The base directory to constrain to
            relative_path: The relative path to append
            
        Returns:
            Secure path within base_dir
            
        Raises:
            InputValidationError: If path would escape base_dir
        """
        # Validate the relative path
        sanitized = self.validate_input(relative_path, input_type="path")
        
        # Resolve paths
        base_resolved = base_dir.resolve()
        target_path = (base_dir / sanitized).resolve()
        
        # Ensure target is within base
        try:
            target_path.relative_to(base_resolved)
        except ValueError:
            raise InputValidationError(
                "path",
                relative_path,
                "Path escapes base directory",
                user_message="Invalid path: cannot access files outside the allowed directory.",
            )
        
        return target_path


# Global security context for convenience
_global_context: SecurityContext | None = None


def get_security_context() -> SecurityContext:
    """Get the global security context."""
    global _global_context
    if _global_context is None:
        _global_context = SecurityContext()
    return _global_context


def set_security_context(context: SecurityContext) -> None:
    """Set the global security context."""
    global _global_context
    _global_context = context


__all__ = [
    "validate_command_input",
    "sanitize_for_shell",
    "ValidationResult",
    "RateLimitConfig",
    "RateLimiter",
    "SecurityContext",
    "get_security_context",
    "set_security_context",
]
