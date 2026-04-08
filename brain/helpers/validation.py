"""Input validation helpers."""

from typing import Literal, Optional, Type, TypeVar, Union

from ..types import Modality, ResponseStyle, DialogueIntent
from .errors import ValidationError

T = TypeVar("T")


def validate_text(text: str, min_length: int = 1, max_length: int = 10000) -> str:
    """Validate and normalize text input.
    
    Normalization includes:
    - Whitespace collapsing
    - Encoding validation
    
    Args:
        text: Text to validate
        min_length: Minimum allowed length (default: 1)
        max_length: Maximum allowed length (default: 10000)
        
    Returns:
        Normalized text
        
    Raises:
        ValidationError: If validation fails
        
    Example:
        >>> validate_text("  hello  world  ")
        'hello world'
    """
    if not isinstance(text, str):
        raise ValidationError(f"Expected string, got {type(text).__name__}", field="text")
    
    # Normalize whitespace
    normalized = " ".join(text.split())
    
    if len(normalized) < min_length:
        raise ValidationError(
            f"Text too short (min {min_length} chars, got {len(normalized)})",
            field="text"
        )
    
    if len(normalized) > max_length:
        raise ValidationError(
            f"Text too long (max {max_length} chars, got {len(normalized)})",
            field="text"
        )
    
    return normalized


def validate_modality(modality: str) -> Modality:
    """Validate modality value.
    
    Args:
        modality: Modality string to validate
        
    Returns:
        Valid modality
        
    Raises:
        ValidationError: If modality is invalid
    """
    valid_modalities = ["text", "voice", "image", "file", "url"]
    
    if modality not in valid_modalities:
        raise ValidationError(
            f"Invalid modality '{modality}'. Must be one of: {', '.join(valid_modalities)}",
            field="modality"
        )
    
    return modality  # type: ignore[return-value]


def validate_confidence(value: float, name: str = "confidence") -> float:
    """Validate confidence score (0.0 to 1.0).
    
    Args:
        value: Confidence value
        name: Field name for error message
        
    Returns:
        Validated confidence value
        
    Raises:
        ValidationError: If value is out of range
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(
            f"Expected number, got {type(value).__name__}",
            field=name
        )
    
    if not 0.0 <= value <= 1.0:
        raise ValidationError(
            f"Must be between 0.0 and 1.0, got {value}",
            field=name
        )
    
    return float(value)


def validate_response_style(style: str) -> ResponseStyle:
    """Validate response style.
    
    Args:
        style: Style string
        
    Returns:
        Valid response style
        
    Raises:
        ValidationError: If style is invalid
    """
    valid_styles = ["concise", "supportive", "stepwise"]
    
    if style not in valid_styles:
        raise ValidationError(
            f"Invalid response style '{style}'. Must be one of: {', '.join(valid_styles)}",
            field="response_style"
        )
    
    return style  # type: ignore[return-value]


def validate_intent(intent: str) -> DialogueIntent:
    """Validate dialogue intent.
    
    Args:
        intent: Intent string
        
    Returns:
        Valid dialogue intent
        
    Raises:
        ValidationError: If intent is invalid
    """
    valid_intents = ["greeting", "code", "factual", "planning", "follow_up", "general"]
    
    if intent not in valid_intents:
        raise ValidationError(
            f"Invalid intent '{intent}'. Must be one of: {', '.join(valid_intents)}",
            field="intent"
        )
    
    return intent  # type: ignore[return-value]


def validate_token_count(count: int, min_val: int = 1, max_val: int = 100000) -> int:
    """Validate token count.
    
    Args:
        count: Token count
        min_val: Minimum allowed
        max_val: Maximum allowed
        
    Returns:
        Validated token count
        
    Raises:
        ValidationError: If invalid
    """
    if not isinstance(count, int):
        raise ValidationError(f"Expected integer, got {type(count).__name__}", field="token_count")
    
    if not min_val <= count <= max_val:
        raise ValidationError(
            f"Token count must be between {min_val} and {max_val}, got {count}",
            field="token_count"
        )
    
    return count


def validate_required(value: Optional[str], field_name: str) -> str:
    """Validate that a value is present.
    
    Args:
        value: Value to check
        field_name: Field name for error message
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is None or empty
    """
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"Required field is missing", field=field_name)
    
    return value
