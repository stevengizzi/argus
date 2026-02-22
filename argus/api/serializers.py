"""Event serialization for WebSocket streaming.

Converts Event dataclasses to JSON-serializable dictionaries for transmission
to WebSocket clients.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from enum import Enum
from typing import Any


def _serialize_value(value: Any) -> Any:
    """Recursively serialize a value to JSON-compatible types.

    Args:
        value: Any value that needs serialization.

    Returns:
        JSON-serializable value.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _serialize_dataclass(value)
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    # Primitives: int, float, str, bool
    return value


def _serialize_dataclass(obj: Any) -> dict[str, Any]:
    """Serialize a dataclass to a dict, handling nested dataclasses.

    Args:
        obj: A dataclass instance.

    Returns:
        Dictionary with all fields serialized.
    """
    result = {}
    for f in dataclasses.fields(obj):
        value = getattr(obj, f.name)
        result[f.name] = _serialize_value(value)
    return result


def serialize_event(event: Any) -> dict[str, Any]:
    """Convert an Event dataclass to a JSON-serializable dict.

    - Uses dataclasses.asdict() pattern for conversion
    - Converts datetime objects to ISO 8601 strings (recursively)
    - Removes 'sequence' from data (it goes in the wrapper message, not the payload)
    - Handles nested dataclasses (e.g., OrderApprovedEvent contains SignalEvent)
    - Falls back to event.__dict__ if dataclass conversion fails

    Args:
        event: An Event dataclass instance.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    try:
        if dataclasses.is_dataclass(event) and not isinstance(event, type):
            data = _serialize_dataclass(event)
        else:
            # Fallback to __dict__ if not a dataclass
            data = {k: _serialize_value(v) for k, v in event.__dict__.items()}
    except Exception:
        # Ultimate fallback
        data = dict(event.__dict__) if hasattr(event, "__dict__") else {}

    # Remove sequence from data - it goes in the wrapper message
    data.pop("sequence", None)

    return data
