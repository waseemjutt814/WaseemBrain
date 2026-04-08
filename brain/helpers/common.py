"""Common utilities and helpers."""

import json
from pathlib import Path
from typing import Any, Optional, TypeVar

T = TypeVar("T")


def safe_json_loads(text: str, default: Optional[Any] = None) -> Any:
    """Safely load JSON, returning default on error.
    
    Args:
        text: JSON string
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safely dump to JSON, returning default on error.
    
    Args:
        obj: Object to serialize
        default: Default JSON string if serialization fails
        
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return default


def deep_get(obj: dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested dictionary value using dot notation.
    
    Args:
        obj: Dictionary to query
        path: Dot-separated path (e.g., "users.0.name")
        default: Default value if not found
        
    Returns:
        Value at path or default
        
    Example:
        deep_get({"a": {"b": "c"}}, "a.b")  # Returns "c"
    """
    keys = path.split(".")
    current = obj
    
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        elif isinstance(current, list):
            try:
                idx = int(key)
                current = current[idx]
            except (ValueError, IndexError):
                return default
        else:
            return default
    
    return current


def deep_set(obj: dict[str, Any], path: str, value: Any) -> None:
    """Set nested dictionary value using dot notation.
    
    Args:
        obj: Dictionary to modify
        path: Dot-separated path
        value: Value to set
        
    Example:
        deep_set(obj, "a.b", "new_value")
    """
    keys = path.split(".")
    current = obj
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge update dict into base dict.
    
    Args:
        base: Base dictionary
        updates: Updates to merge in
        
    Returns:
        Merged dictionary (doesn't modify originals)
    """
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, creating if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        The directory path
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_file_dir(file_path: Path) -> Path:
    """Ensure parent directory of file exists.
    
    Args:
        file_path: File path
        
    Returns:
        The file path
    """
    ensure_dir(file_path.parent)
    return file_path


def read_json_file(path: Path, default: Optional[Any] = None) -> Any:
    """Read and parse JSON file safely.
    
    Args:
        path: File path
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Parsed JSON or default value
    """
    if not path.exists():
        return default
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def write_json_file(path: Path, data: Any, pretty: bool = True) -> None:
    """Write data as JSON file.
    
    Args:
        path: File path
        data: Data to write
        pretty: Whether to pretty-print
    """
    ensure_file_dir(path)
    
    with open(path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, default=str)
        else:
            json.dump(data, f, default=str)


def chunks(items: list[T], size: int) -> list[list[T]]:
    """Split list into chunks of given size.
    
    Args:
        items: List to split
        size: Chunk size
        
    Returns:
        List of chunks
        
    Example:
        chunks([1,2,3,4,5], 2)  # [[1,2], [3,4], [5]]
    """
    return [items[i:i + size] for i in range(0, len(items), size)]


def flatten(nested_list: list[list[T]]) -> list[T]:
    """Flatten a nested list.
    
    Args:
        nested_list: Nested list
        
    Returns:
        Flattened list
    """
    return [item for sublist in nested_list for item in sublist]


def unique_preserve_order(items: list[T]) -> list[T]:
    """Get unique items preserving order.
    
    Args:
        items: List of items
        
    Returns:
        List with unique items in original order
    """
    seen: set[Any] = set()
    result: list[T] = []
    
    for item in items:
        try:
            if item not in seen:
                seen.add(item)
                result.append(item)
        except TypeError:
            # Item is unhashable, add if not already present
            if item not in result:
                result.append(item)
    
    return result


def invert_dict(d: dict[str, str]) -> dict[str, str]:
    """Invert dictionary keys and values.
    
    Args:
        d: Dictionary to invert
        
    Returns:
        Inverted dictionary
    """
    return {v: k for k, v in d.items()}


def find_diffs(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Find differences between two dicts.
    
    Args:
        old: Original dictionary
        new: New dictionary
        
    Returns:
        Dictionary with changes
    """
    diffs = {
        "added": {},
        "removed": {},
        "changed": {},
    }
    
    # Find removed and changed
    for key, old_val in old.items():
        if key not in new:
            diffs["removed"][key] = old_val
        elif new[key] != old_val:
            diffs["changed"][key] = {"old": old_val, "new": new[key]}
    
    # Find added
    for key, new_val in new.items():
        if key not in old:
            diffs["added"][key] = new_val
    
    return diffs


def resolve_type_name(value: Any) -> str:
    """Get human-readable type name for value.
    
    Args:
        value: Value to inspect
        
    Returns:
        Type name
    """
    if value is None:
        return "None"
    
    t = type(value).__name__
    
    # Special cases
    if t == "dict":
        return f"dict({len(value)})"
    elif t == "list":
        return f"list({len(value)})"
    elif t == "str":
        return f"str({len(value)})"
    
    return t
