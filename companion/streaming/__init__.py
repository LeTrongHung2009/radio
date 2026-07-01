"""
Streaming Platform Integration Module
======================================

Manages connections to Twitch, YouTube, and other streaming platforms.
Handles chat reading, message posting, and platform-specific features.
"""

from .twitch_bot import TwitchBot
from .youtube_bot import YouTubeBot
from .platform_manager import ChatPlatformManager
from .chat_message import ChatMessage, ChatPlatform, ChatUser
from .stream_events import StreamEvent, EventType

__all__ = [
    'TwitchBot',
    'YouTubeBot', 
    'ChatPlatformManager',
    'get_chat_platform_manager',
    'ChatMessage',
    'ChatPlatform',
    'ChatUser',
    'StreamEvent',
    'EventType',
]

from companion.utils.singleton import singletons


def get_chat_platform_manager() -> ChatPlatformManager:
    """Get or create the singleton chat platform manager."""
    return singletons.get_or_create(ChatPlatformManager)
