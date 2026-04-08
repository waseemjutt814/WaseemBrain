"""Reusable decorators for Waseem Brain functions.

Provides commonly used decorators for timing, caching, retries, rate limiting,
validation, and debugging. All decorators preserve function metadata with
functools.wraps and integrate with the logging system.

Example:
    >>> @timer(name="search_operation")
    >>> @cached(ttl_seconds=300)
    >>> @retry(max_attempts=3)
    >>> def search_memory(query: str) -> list[dict]:
    ...     return memory.search(query)
"""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from .logger import get_logger
from .timing import PerformanceMonitor

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def timer(name: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to measure function execution time.
    
    Logs execution time at DEBUG level. Useful for performance monitoring
    and identifying bottlenecks.
    
    Args:
        name: Optional operation name (defaults to module.function)
        
    Returns:
        Decorated function with timing instrumentation
        
    Example:
        >>> @timer("expensive_operation")
        >>> def compute_something(data):
        ...     # expensive computation
        ...     return result
        # DEBUG: expensive_operation: 245.32ms
    """
    def decorator(func: F) -> F:
        op_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start) * 1000
                logger.debug(f"{op_name}: {elapsed_ms:.2f}ms")
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


def cached(ttl_seconds: int = 300) -> Callable[[F], F]:
    """Decorator to cache function results with time-to-live.
    
    Caches results based on function arguments. Cache entries expire after
    ttl_seconds. Additional methods: cache_clear(), cache_info().
    
    Args:
        ttl_seconds: Time-to-live for cached items in seconds (default: 300)
        
    Returns:
        Decorated function with result caching
        
    Example:
        >>> @cached(ttl_seconds=600)
        >>> def get_expert_config(expert_id: str):
        ...     return load_config(expert_id)
        
        >>> get_expert_config.cache_info()
        {'size': 2, 'ttl_seconds': 600}
        
        >>> get_expert_config.cache_clear()
    """
    def decorator(func: F) -> F:
        cache: dict[Any, tuple[Any, float]] = {}
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create cache key from args and kwargs
            key = (args, tuple(sorted(kwargs.items())))
            
            # Check cache
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit: {func.__name__}")
                    return result
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        
        # Add cache management
        wrapper.cache_clear = lambda: cache.clear()  # type: ignore[attr-defined]
        wrapper.cache_info = lambda: {  # type: ignore[attr-defined]
            "size": len(cache),
            "ttl_seconds": ttl_seconds,
        }
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


def retry(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_factor: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator to retry function on failure with exponential backoff.
    
    Retries failed function calls with configurable delay and backoff.
    Logs retry attempts and final failure.
    
    Args:
        max_attempts: Number of attempts before giving up (default: 3)
        delay_seconds: Initial delay between retries in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each retry (default: 1.0)
        exceptions: Exception types to catch and retry (default: all)
        
    Returns:
        Decorated function with automatic retry logic
        
    Example:
        >>> @retry(max_attempts=3, delay_seconds=0.5, backoff_factor=2.0)
        >>> def call_remote_api(url: str):
        ...     return requests.get(url)
        
        # Retries with delay: 0.5s, 1.0s, 2.0s on failure
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            delay = delay_seconds
            
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.debug(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    return result
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts")
            
            raise last_exception or Exception(f"Failed after {max_attempts} attempts")
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


def ratelimit(calls_per_second: float = 10.0) -> Callable[[F], F]:
    """Decorator to rate limit function calls.
    
    Ensures function is called no more than the specified rate by adding
    delays between calls as needed.
    
    Args:
        calls_per_second: Maximum calls per second (default: 10.0)
        
    Returns:
        Decorated function with rate limiting
        
    Example:
        >>> @ratelimit(calls_per_second=5.0)
        >>> def query_external_api(endpoint: str):
        ...     return api.query(endpoint)
    """
    min_interval = 1.0 / calls_per_second
    last_call: dict[str, float] = {"time": 0.0}
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            elapsed = time.time() - last_call["time"]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            
            last_call["time"] = time.time()
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


def validate_args(**validators: Callable[[Any], bool]) -> Callable[[F], F]:
    """Decorator to validate function arguments before execution.
    
    Takes validator functions for each argument. Validators receive the
    argument value and return True if valid, False otherwise.
    
    Args:
        **validators: Mapping of argument names to validation functions
        
    Returns:
        Decorated function with argument validation
        
    Raises:
        ValueError: If any argument fails validation
        
    Example:
        >>> @validate_args(
        ...     email=lambda x: "@" in x,
        ...     age=lambda x: isinstance(x, int) and x > 0,
        ... )
        >>> def create_user(email: str, age: int):
        ...     return User(email, age)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Validate
            for param_name, validator in validators.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not validator(value):
                        raise ValueError(f"Validation failed for parameter: {param_name}")
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


def debug(verbose: bool = True) -> Callable[[F], F]:
    """Decorator to log function calls and results for debugging.
    
    Logs function name, arguments, return value, and any exceptions at
    DEBUG and ERROR levels.
    
    Args:
        verbose: Whether to log full details (default: True)
        
    Returns:
        Decorated function with debug logging
        
    Example:
        >>> @debug()
        >>> def process_data(items: list, threshold: float):
        ...     return [x for x in items if x > threshold]
        
        # DEBUG: process_data called with args=([1,2,3], 1.5)
        # DEBUG: process_data returned: [2, 3]
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if verbose:
                logger.debug(f"Calling {func.__name__}")
                logger.debug(f"  args: {args}")
                logger.debug(f"  kwargs: {kwargs}")
            
            try:
                result = func(*args, **kwargs)
                if verbose:
                    logger.debug(f"{func.__name__} returned: {result}")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised: {e}")
                raise
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


def ensure_type(**type_checks: type) -> Callable[[F], F]:
    """Decorator to enforce type checking on function arguments.
    
    Uses isinstance() to validate argument types before function execution.
    
    Args:
        **type_checks: Mapping of argument names to expected types
        
    Returns:
        Decorated function with type checking
        
    Raises:
        TypeError: If any argument type does not match expected type
        
    Example:
        >>> @ensure_type(name=str, count=int, items=list)
        >>> def process(name: str, count: int, items: list):
        ...     return [f"{name}_{i}" for i in range(count)]
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            for param_name, expected_type in type_checks.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not isinstance(value, expected_type):
                        raise TypeError(
                            f"{param_name} must be {expected_type.__name__}, "
                            f"got {type(value).__name__}"
                        )
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore[return-value]
    
    return decorator
