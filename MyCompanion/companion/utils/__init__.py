"""
Miku AI Companion - Shared utilities.

Provides common patterns used across the companion framework:
- singleton: Singleton instance management
- async_helpers: Async dispatch and invocation utilities
- serialization: Data model serialization helpers
"""

from .singleton import SingletonManager, singletons
from .async_helpers import invoke_method, dispatch_handlers
from .serialization import serialize_value, dataclass_to_dict

__all__ = [
    'SingletonManager',
    'singletons',
    'invoke_method',
    'dispatch_handlers',
    'serialize_value',
    'dataclass_to_dict',
]
