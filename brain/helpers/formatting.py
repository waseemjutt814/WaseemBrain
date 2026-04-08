"""Data formatting and display utilities."""

from typing import Optional


def format_bytes(num_bytes: int) -> str:
    """Format bytes as human-readable string.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Human-readable string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    
    return f"{num_bytes:.1f} PB"


def format_duration(milliseconds: float) -> str:
    """Format duration as human-readable string.
    
    Args:
        milliseconds: Duration in milliseconds
        
    Returns:
        Human-readable string (e.g., "1.2s", "500ms")
    """
    if milliseconds < 1000:
        return f"{milliseconds:.0f}ms"
    elif milliseconds < 60000:
        return f"{milliseconds / 1000:.1f}s"
    else:
        minutes = milliseconds / 60000
        return f"{minutes:.1f}m"


def format_confidence(confidence: float) -> str:
    """Format confidence score as percentage.
    
    Args:
        confidence: Confidence value (0.0-1.0)
        
    Returns:
        Formatted percentage string
    """
    percentage = confidence * 100
    return f"{percentage:.0f}%"


def format_confidence_detailed(confidence: float) -> str:
    """Format confidence with visual indicator.
    
    Args:
        confidence: Confidence value (0.0-1.0)
        
    Returns:
        Formatted string with bar indicator
    """
    percentage = confidence * 100
    
    # Create bar
    filled = int(percentage / 5)  # 20 chars total
    empty = 20 - filled
    bar = "█" * filled + "░" * empty
    
    return f"{bar} {percentage:.0f}%"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_list(items: list[str], conjunction: str = "and") -> str:
    """Format list of items as readable string.
    
    Args:
        items: List of items
        conjunction: Word to use before last item (and/or)
        
    Returns:
        Formatted string (e.g., "apple, banana and cherry")
    """
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    
    return ", ".join(items[:-1]) + f" {conjunction} {items[-1]}"


def format_json_snippet(text: str, max_length: int = 200) -> str:
    """Format JSON snippet for display (minified).
    
    Args:
        text: JSON text to format
        max_length: Maximum display length
        
    Returns:
        Minified and truncated JSON
    """
    # Remove whitespace
    minified = " ".join(text.split())
    return truncate_text(minified, max_length)


def format_code_snippet(code: str, max_lines: int = 5) -> str:
    """Format code snippet for display.
    
    Args:
        code: Code to display
        max_lines: Maximum number of lines
        
    Returns:
        Formatted code snippet
    """
    lines = code.split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["..."]
    
    return "\n".join(lines)


def format_tokens_estimate(text: str) -> int:
    """Estimate token count for text (rough).
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count
    """
    # Rough estimate: 1 token ≈ 4 characters
    return max(1, len(text) // 4)


def format_url(url: str, max_length: int = 50) -> str:
    """Format URL for display.
    
    Args:
        url: URL to format
        max_length: Maximum display length
        
    Returns:
        Formatted URL
    """
    if len(url) <= max_length:
        return url
    
    # Try to shorten while keeping domain
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path[:max_length - len(domain) - 3] + "..."
        return domain + path
    except Exception:
        return truncate_text(url, max_length)


def format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp as readable string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted date/time string
    """
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def format_error_message(error_code: str, detail: str = "") -> str:
    """Format error message for display.
    
    Args:
        error_code: Error code
        detail: Additional detail
        
    Returns:
        Formatted error message
    """
    msg = f"Error [{error_code}]"
    if detail:
        msg += f": {detail}"
    return msg
