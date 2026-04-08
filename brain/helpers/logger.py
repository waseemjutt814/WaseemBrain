"""Logging utilities for Waseem Brain."""

import logging
import sys
from typing import Optional

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger for the given name.
    
    Uses module-level caching to avoid duplicate logger instances.
    
    Args:
        name: Logger name, typically __name__ of the calling module
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger


def configure_logging(
    level: int = logging.INFO,
    format_str: Optional[str] = None,
    file_path: Optional[str] = None,
) -> None:
    """Configure logging for the entire Brain application.
    
    Configures the root logger with optional file output.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR) (default: INFO)
        format_str: Log message format string (default: timestamp + level + message)
        file_path: Optional file to log to in addition to stderr
        
    Example:
        >>> configure_logging(level=logging.DEBUG, file_path="brain.log")
    """
    if format_str is None:
        format_str = (
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
        )
    
    formatter = logging.Formatter(format_str)
    
    # Configure root logger
    root = logging.getLogger()
    root.setLevel(level)
    
    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Add stderr handler
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(level)
    root.addHandler(stderr_handler)
    
    # Add file handler if specified
    if file_path:
        try:
            file_handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            root.addHandler(file_handler)
        except (OSError, IOError) as e:
            root.warning(f"Failed to add file handler: {e}")


def log_exception(
    logger: logging.Logger,
    exc: Exception,
    context: str = "",
) -> None:
    """Log an exception with optional context.
    
    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context message (e.g., operation name)
        
    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(logger, e, context="risky_operation")
    """
    if context:
        logger.exception(f"{context}: {exc.__class__.__name__}")
    else:
        logger.exception(f"{exc.__class__.__name__}: {exc}")
