"""Brain helpers and utilities.

This package provides comprehensive helper modules:
- logger: Logging configuration and utilities
- errors: Custom exceptions and error handling
- timing: Performance monitoring and timing
- validation: Input validation helpers
- formatting: Data formatting and display
- decorators: Useful decorators (timer, cache, retry, etc.)
- testing: Testing utilities and fixtures
- common: General utilities and patterns
"""

# Decorators
from .decorators import (
    timer,
    cached,
    retry,
    ratelimit,
    validate_args,
    debug,
    ensure_type,
)

# Errors
from .errors import (
    BrainError,
    ValidationError,
    ConfigError,
    RuntimeError as BrainRuntimeError,
    TimeoutError,
    NotFoundError,
    ConflictError,
    UnsupportedError,
)

# Formatting
from .formatting import (
    format_bytes,
    format_duration,
    format_confidence,
    format_confidence_detailed,
    truncate_text,
    format_list,
    format_json_snippet,
    format_code_snippet,
    format_tokens_estimate,
    format_url,
    format_timestamp,
    format_error_message,
)

# Logging
from .logger import get_logger, configure_logging, log_exception

# Timing
from .timing import Timer, PerformanceMonitor, timer as timer_context, TimerResult

# Validation
from .validation import (
    validate_text,
    validate_modality,
    validate_confidence,
    validate_response_style,
    validate_intent,
    validate_token_count,
    validate_required,
)

# Testing
from .testing import (
    MockQuery,
    MockResponse,
    create_test_memory_node,
    assert_valid_response,
    assert_valid_trace,
    TestRegistry,
    register_fixture,
    get_fixture,
    create_mock_runtime,
)

# Common utilities
from .common import (
    safe_json_loads,
    safe_json_dumps,
    deep_get,
    deep_set,
    merge_dicts,
    ensure_dir,
    ensure_file_dir,
    read_json_file,
    write_json_file,
    chunks,
    flatten,
    unique_preserve_order,
    invert_dict,
    find_diffs,
    resolve_type_name,
)

__all__ = [
    # Decorators
    "timer",
    "cached",
    "retry",
    "ratelimit",
    "validate_args",
    "debug",
    "ensure_type",
    # Errors
    "BrainError",
    "ValidationError",
    "ConfigError",
    "BrainRuntimeError",
    "TimeoutError",
    "NotFoundError",
    "ConflictError",
    "UnsupportedError",
    # Formatting
    "format_bytes",
    "format_duration",
    "format_confidence",
    "format_confidence_detailed",
    "truncate_text",
    "format_list",
    "format_json_snippet",
    "format_code_snippet",
    "format_tokens_estimate",
    "format_url",
    "format_timestamp",
    "format_error_message",
    # Logging
    "get_logger",
    "configure_logging",
    "log_exception",
    # Timing
    "Timer",
    "PerformanceMonitor",
    "timer_context",
    "TimerResult",
    # Validation
    "validate_text",
    "validate_modality",
    "validate_confidence",
    "validate_response_style",
    "validate_intent",
    "validate_token_count",
    "validate_required",
    # Testing
    "MockQuery",
    "MockResponse",
    "create_test_memory_node",
    "assert_valid_response",
    "assert_valid_trace",
    "TestRegistry",
    "register_fixture",
    "get_fixture",
    "create_mock_runtime",
    # Common
    "safe_json_loads",
    "safe_json_dumps",
    "deep_get",
    "deep_set",
    "merge_dicts",
    "ensure_dir",
    "ensure_file_dir",
    "read_json_file",
    "write_json_file",
    "chunks",
    "flatten",
    "unique_preserve_order",
    "invert_dict",
    "find_diffs",
    "resolve_type_name",
]
