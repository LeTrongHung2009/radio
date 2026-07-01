"""
Singleton pattern utilities for managing global instances.

Eliminates the repeated get_X / initialize_X boilerplate found across modules.
"""

import logging
from typing import TypeVar, Type, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SingletonManager:
    """
    Generic singleton registry that replaces the repeated pattern of:

        _instance: Optional[MyClass] = None

        def get_my_class() -> MyClass:
            global _instance
            if _instance is None:
                _instance = MyClass()
            return _instance

        def initialize_my_class(...) -> MyClass:
            global _instance
            _instance = MyClass(...)
            return _instance

    Usage:
        singletons = SingletonManager()

        def get_config() -> Config:
            return singletons.get_or_create(Config)

        def initialize_config(**kwargs) -> Config:
            return singletons.create(Config, **kwargs)
    """

    def __init__(self):
        self._instances: dict[type, object] = {}

    def get(self, cls: Type[T]) -> Optional[T]:
        """Get an existing singleton instance, or None if not created."""
        return self._instances.get(cls)

    def get_or_create(self, cls: Type[T], *args, **kwargs) -> T:
        """Get an existing instance, or create one with the given arguments."""
        if cls not in self._instances:
            self._instances[cls] = cls(*args, **kwargs)
            logger.debug(f"Created singleton: {cls.__name__}")
        return self._instances[cls]

    def create(self, cls: Type[T], *args, **kwargs) -> T:
        """Create (or replace) a singleton instance."""
        self._instances[cls] = cls(*args, **kwargs)
        logger.debug(f"Initialized singleton: {cls.__name__}")
        return self._instances[cls]

    def get_or_raise(self, cls: Type[T]) -> T:
        """Get an existing instance, raising RuntimeError if not initialized."""
        instance = self._instances.get(cls)
        if instance is None:
            raise RuntimeError(f"{cls.__name__} not initialized!")
        return instance

    def reset(self, cls: Type[T]) -> None:
        """Remove a singleton instance."""
        if cls in self._instances:
            del self._instances[cls]
            logger.debug(f"Reset singleton: {cls.__name__}")


singletons = SingletonManager()
