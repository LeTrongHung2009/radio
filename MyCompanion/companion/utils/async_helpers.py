"""
Async helper utilities for common patterns.

Consolidates repeated async dispatch and agent invocation patterns.
"""

import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


async def invoke_method(obj: object, method_name: str, *args, **kwargs) -> Any:
    """
    Invoke a method on an object, handling both sync and async variants.

    Replaces the repeated pattern:
        if hasattr(agent, 'start'):
            if asyncio.iscoroutinefunction(agent.start):
                await agent.start()
            else:
                agent.start()

    Usage:
        await invoke_method(agent, 'start')
        await invoke_method(agent, 'execute_action', action, params)

    Returns:
        The method's return value, or None if the method doesn't exist.
    """
    method = getattr(obj, method_name, None)
    if method is None:
        return None

    if asyncio.iscoroutinefunction(method):
        return await method(*args, **kwargs)
    return method(*args, **kwargs)


async def dispatch_handlers(
    handlers: list[Callable],
    *args,
    error_label: str = "handler",
    **kwargs,
) -> None:
    """
    Call a list of handlers (sync or async) with the given arguments,
    catching and logging errors per handler.

    Replaces the repeated pattern:
        for handler in self.handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in handler: {e}")

    Usage:
        await dispatch_handlers(self.message_handlers, message,
                                error_label="message handler")
    """
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(*args, **kwargs)
            else:
                handler(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {error_label}: {e}")
