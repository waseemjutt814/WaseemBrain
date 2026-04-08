"""Performance timing and monitoring utilities.

Provides utilities for measuring execution time of operations and tracking
performance metrics over time. Includes Timer context manager and
PerformanceMonitor for collecting aggregate statistics like percentiles.

Example:
    >>> with Timer("search_operation"):
    ...     results = memory.search(query)
    >>> DEBUG: search_operation: 45.23ms
    
    >>> monitor = PerformanceMonitor("api_calls")
    >>> monitor.record(123.5)
    >>> monitor.summary()
    {'count': 1, 'min_ms': 123.5, 'max_ms': 123.5, 'p50': 123.5, 'p95': 123.5}
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, Optional

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class TimerResult:
    """Result of a timing operation.
    
    Attributes:
        operation: Name of the timed operation
        elapsed_ms: Elapsed time in milliseconds
        start_time: Unix timestamp when timer started
        end_time: Unix timestamp when timer ended
    """
    
    operation: str
    elapsed_ms: float
    start_time: float
    end_time: float
    
    def __str__(self) -> str:
        return f"{self.operation}: {self.elapsed_ms:.2f}ms"
    
    def __repr__(self) -> str:
        return f"TimerResult(operation='{self.operation}', elapsed_ms={self.elapsed_ms:.2f})"


class Timer:
    """Simple timer context manager for measuring execution time.
    
    Automatically logs elapsed time at DEBUG level when used as context manager.
    
    Args:
        operation: Name of the operation being timed
        log: Whether to log the result at exit (default: True)
        
    Attributes:
        start_time: Unix timestamp when timer started
        end_time: Unix timestamp when timer ended
        elapsed_ms: Elapsed time in milliseconds
        
    Example:
        >>> with Timer("database_query") as t:
        ...     results = db.execute_query()
        >>> print(f"Query took {t.elapsed_ms:.2f}ms")
    """
    
    def __init__(self, operation: str = "Operation", log: bool = True) -> None:
        """Initialize Timer.
        
        Args:
            operation: Description of the operation being timed
            log: Whether to log at exit (default: True)
        """
        self.operation = operation
        self.log = log
        self.start_time: float = 0.0
        self.end_time: float = 0.0
    
    def __enter__(self) -> "Timer":
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timing and log if enabled."""
        self.end_time = time.time()
        elapsed_ms = (self.end_time - self.start_time) * 1000
        
        if self.log:
            logger.debug(f"{self.operation}: {elapsed_ms:.2f}ms")
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.end_time == 0.0:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000
    
    @property
    def result(self) -> TimerResult:
        """Get detailed timer result."""
        return TimerResult(
            operation=self.operation,
            elapsed_ms=self.elapsed_ms,
            start_time=self.start_time,
            end_time=self.end_time,
        )


@contextmanager
def timer(operation: str = "Operation", log: bool = True) -> Iterator[Timer]:
    """Context manager for timing operations.
    
    Yields a Timer that tracks elapsed time, with automatic logging.
    
    Args:
        operation: Name of the operation being timed
        log: Whether to log result at exit (default: True)
        
    Yields:
        Timer instance with elapsed_ms property
        
    Example:
        >>> with timer("data_processing") as t:
        ...     process_data(items)
        >>> print(f"Took {t.elapsed_ms:.2f}ms")
    """
    t = Timer(operation, log=log)
    try:
        with t:
            yield t
    except Exception:
        raise


@dataclass
class PerformanceMonitor:
    """Monitor and aggregate performance metrics over time.
    
    Tracks measurements and computes statistics including averages,
    minimums, maximums, and percentiles.
    
    Attributes:
        name: Name of the monitored operation
        
    Example:
        >>> monitor = PerformanceMonitor("api_requests")
        >>> for response in requests:
        ...     monitor.record(response.elapsed_ms)
        >>> print(monitor.summary())
        {'count': 100, 'min_ms': 10.2, 'max_ms': 500.1, ...}
    """
    
    name: str
    _measurements: list[float] = field(default_factory=list)
    _count: int = 0
    _total: float = 0.0
    _min: float = float('inf')
    _max: float = 0.0
    
    def record(self, elapsed_ms: float) -> None:
        """Record a performance measurement.
        
        Args:
            elapsed_ms: Elapsed time in milliseconds
        """
        self._measurements.append(elapsed_ms)
        self._count += 1
        self._total += elapsed_ms
        self._min = min(self._min, elapsed_ms)
        self._max = max(self._max, elapsed_ms)
    
    @property
    def count(self) -> int:
        """Number of measurements recorded."""
        return self._count
    
    @property
    def total(self) -> float:
        """Total time in milliseconds."""
        return self._total
    
    @property
    def average(self) -> float:
        """Average time in milliseconds."""
        return self._total / self._count if self._count > 0 else 0.0
    
    @property
    def min(self) -> float:
        """Minimum time in milliseconds."""
        return self._min if self._count > 0 else 0.0
    
    @property
    def max(self) -> float:
        """Maximum time in milliseconds."""
        return self._max if self._count > 0 else 0.0
    
    @property
    def p50(self) -> float:
        """50th percentile (median)."""
        if not self._measurements:
            return 0.0
        sorted_vals = sorted(self._measurements)
        idx = len(sorted_vals) // 2
        return sorted_vals[idx]
    
    @property
    def p95(self) -> float:
        """95th percentile."""
        if not self._measurements:
            return 0.0
        sorted_vals = sorted(self._measurements)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[idx] if idx < len(sorted_vals) else sorted_vals[-1]
    
    @property
    def p99(self) -> float:
        """99th percentile."""
        if not self._measurements:
            return 0.0
        sorted_vals = sorted(self._measurements)
        idx = int(len(sorted_vals) * 0.99)
        return sorted_vals[idx] if idx < len(sorted_vals) else sorted_vals[-1]
    
    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"{self.name}: "
            f"count={self.count} "
            f"avg={self.average:.2f}ms "
            f"min={self.min:.2f}ms "
            f"max={self.max:.2f}ms "
            f"p95={self.p95:.2f}ms"
        )
    
    def reset(self) -> None:
        """Clear all measurements."""
        self._measurements.clear()
        self._count = 0
        self._total = 0.0
        self._min = float('inf')
        self._max = 0.0
