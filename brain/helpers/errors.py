"""Custom exceptions for Waseem Brain.

All custom exceptions derive from BrainError and provide structured error
information including consistent error codes for programmatic handling.

Example:
    >>> try:
    ...     validate_user_input(text)
    ... except ValidationError as e:
    ...     logger.error(f"Validation failed: {e.message}")
"""


class BrainError(Exception):
    """Base exception for all Brain-related errors.
    
    Provides consistent error handling with codes for programmatic handling.
    
    Attributes:
        message: Human-readable error message
        code: Machine-readable error code for categorization
    """
    
    def __init__(self, message: str, code: str = "BRAIN_ERROR") -> None:
        """Initialize BrainError.
        
        Args:
            message: Descriptive error message
            code: Error code for classification (default: BRAIN_ERROR)
        """
        self.message = message
        self.code = code
        super().__init__(f"[{code}] {message}")


class ValidationError(BrainError):
    """Raised when input validation fails.
    
    Used for invalid input data, structural violations, or constraint failures.
    
    Attributes:
        field: Field name that failed validation (if applicable)
        
    Example:
        >>> if not text or len(text) > 10000:
        ...     raise ValidationError("Text too long", field="text")
    """
    
    def __init__(self, message: str, field: str = "") -> None:
        """Initialize ValidationError.
        
        Args:
            message: Description of validation failure
            field: Optional field name that failed validation
        """
        prefix = f"Validation failed for {field}: " if field else "Validation failed: "
        super().__init__(prefix + message, "VALIDATION_ERROR")
        self.field = field


class ConfigError(BrainError):
    """Raised when configuration is invalid or missing.
    
    Used for configuration issues like missing keys, invalid values, or
    incomplete settings.
    
    Attributes:
        key: Configuration key that has the error (if applicable)
        
    Example:
        >>> if not config.get("model_path"):
        ...     raise ConfigError("model_path required for init", key="model_path")
    """
    
    def __init__(self, message: str, key: str = "") -> None:
        """Initialize ConfigError.
        
        Args:
            message: Description of configuration problem
            key: Optional configuration key that has the problem
        """
        prefix = f"Config error for {key}: " if key else "Config error: "
        super().__init__(prefix + message, "CONFIG_ERROR")
        self.key = key


class RuntimeError(BrainError):
    """Raised during unexpected runtime execution failures.
    
    Used for errors that occur while the system is running operations,
    not configuration or validation issues.
    
    Attributes:
        context: Operation context that failed (if applicable)
        
    Example:
        >>> try:
        ...     result = memory.search(query)
        ... except Exception as e:
        ...     raise RuntimeError("Search failed", context="memory.search")
    """
    
    def __init__(self, message: str, context: str = "") -> None:
        """Initialize RuntimeError.
        
        Args:
            message: Description of runtime failure
            context: Optional context describing what operation failed
        """
        prefix = f"Runtime error in {context}: " if context else "Runtime error: "
        super().__init__(prefix + message, "RUNTIME_ERROR")
        self.context = context


class TimeoutError(BrainError):
    """Raised when an operation exceeds its time limit.
    
    Attributes:
        operation: Name of the operation that timed out
        timeout_sec: Timeout duration in seconds
        
    Example:
        >>> if elapsed > timeout:
        ...     raise TimeoutError(operation="semantic_search", timeout_sec=30.0)
    """
    
    def __init__(self, operation: str, timeout_sec: float) -> None:
        """Initialize TimeoutError.
        
        Args:
            operation: Name of the operation that timed out
            timeout_sec: Timeout duration in seconds
        """
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_sec}s",
            "TIMEOUT_ERROR"
        )
        self.operation = operation
        self.timeout_sec = timeout_sec


class NotFoundError(BrainError):
    """Raised when a required resource cannot be found.
    
    Attributes:
        resource_type: Type of resource not found (e.g., "Expert", "MemoryNode")
        resource_id: Identifier of the resource not found
        
    Example:
        >>> if not memory_node:
        ...     raise NotFoundError("MemoryNode", "node_uuid_123")
    """
    
    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize NotFoundError.
        
        Args:
            resource_type: Type of resource that was not found
            resource_id: Identifier of the missing resource
        """
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            "NOT_FOUND_ERROR"
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictError(BrainError):
    """Raised when an operation conflicts with existing state.
    
    Used when trying to create duplicate resources, modify locked items, or
    perform operations that violate current state constraints.
    
    Attributes:
        existing: Description of the existing state causing the conflict
        
    Example:
        >>> if expert_name in registry:
        ...     raise ConflictError("Expert already registered", existing=expert_id)
    """
    
    def __init__(self, message: str, existing: str = "") -> None:
        """Initialize ConflictError.
        
        Args:
            message: Description of the conflict
            existing: Optional description of existing state causing conflict
        """
        full_msg = f"{message} (existing: {existing})" if existing else message
        super().__init__(full_msg, "CONFLICT_ERROR")
        self.existing = existing


class UnsupportedError(BrainError):
    """Raised when a feature or operation is not supported.
    
    Used for operations that are out of scope or not available in the current
    configuration.
    
    Attributes:
        feature: Feature or operation that is not supported
        reason: Optional explanation for why it's not supported
        
    Example:
        >>> if modality not in SUPPORTED_MODALITIES:
        ...     raise UnsupportedError(f"Audio modality", reason="audio model unavailable")
    """
    
    def __init__(self, feature: str, reason: str = "") -> None:
        """Initialize UnsupportedError.
        
        Args:
            feature: Feature or operation that is not supported
            reason: Optional explanation for why it's unsupported
        """
        msg = f"Unsupported: {feature}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg, "UNSUPPORTED_ERROR")
        self.feature = feature
        self.reason = reason
