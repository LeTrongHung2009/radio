"""
Serialization helpers for data models.

Provides utilities for the repeated to_dict patterns found across
dataclasses (enum-to-name, datetime-to-isoformat, nested to_dict).
"""

from datetime import datetime
from enum import Enum
from typing import Any


def serialize_value(value: Any) -> Any:
    """
    Recursively serialize a value for JSON-safe dict output.

    Handles:
    - Enum -> name string
    - datetime -> ISO format string
    - Objects with a to_dict() method -> call it
    - Lists / dicts -> recurse
    - Primitives -> pass through
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.name if hasattr(value, 'name') else value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, 'to_dict'):
        return value.to_dict()
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def dataclass_to_dict(obj: object, fields: list[str]) -> dict:
    """
    Convert a dataclass-like object to a dict, serializing each listed field.

    Replaces hand-written to_dict() methods that repeat the same
    enum/datetime/nested-object conversion for every field.

    Usage:
        def to_dict(self) -> dict:
            return dataclass_to_dict(self, [
                'game_id', 'game_name', 'is_active', 'is_paused',
                'last_action', 'last_action_time', 'session_start',
            ])
    """
    result = {}
    for field_name in fields:
        value = getattr(obj, field_name, None)
        result[field_name] = serialize_value(value)
    return result
