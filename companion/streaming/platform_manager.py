"""
Chat Platform Manager
=====================

Manages multiple streaming platform connections and provides unified interface.
"""

import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

from ..config import get_config
from .chat_message import ChatMessage, ChatPlatform, ChatUser
from .stream_events import StreamEvent, EventType
from .twitch_bot import TwitchBotHandler
from .youtube_bot import YouTubeBot
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class ChatPlatformManager:
    """Manages connections to multiple streaming platforms."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.config = get_config()
        self.event_bus = event_bus or EventBus.get_instance()
        
        self.twitch_handler: Optional[TwitchBotHandler] = None
        self.youtube_handler: Optional[YouTubeBotHandler] = None
        
        self.connected_platforms: set[ChatPlatform] = set()
        self.message_handlers: list[Callable] = []
        self.event_handlers: list[Callable] = []
        
        self._running = False
        
    async def initialize(self):
        """Initialize all platform handlers."""
        # Initialize Twitch
        if self.config.TWITCH_OAUTH_TOKEN and self.config.TWITCH_BOT_USERNAME:
            self.twitch_handler = TwitchBotHandler(self.config, self.event_bus)
            
        # Initialize YouTube
        if self.config.GOOGLE_API_KEY and self.config.YOUTUBE_CHANNEL_ID:
            self.youtube_handler = YouTubeBotHandler(self.config, self.event_bus)
            
        # Subscribe to events
        await self.event_bus.subscribe('chat_message', self._on_chat_message)
        await self.event_bus.subscribe('stream_event', self._on_stream_event)
        
        logger.info(f"Chat platform manager initialized. Platforms: {len(self.connected_platforms)}")
        
    async def connect_all(self):
        """Connect to all configured platforms."""
        self._running = True
        
        tasks = []
        
        if self.twitch_handler:
            tasks.append(self._connect_twitch())
            
        if self.youtube_handler:
            tasks.append(self._connect_youtube())
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def _connect_twitch(self):
        """Connect to Twitch."""
        try:
            await self.twitch_handler.connect()
            if self.twitch_handler.is_connected:
                self.connected_platforms.add(ChatPlatform.TWITCH)
                logger.info("Connected to Twitch")
        except Exception as e:
            logger.error(f"Failed to connect to Twitch: {e}")
            
    async def _connect_youtube(self):
        """Connect to YouTube."""
        try:
            await self.youtube_handler.connect()
            if self.youtube_handler.is_connected:
                self.connected_platforms.add(ChatPlatform.YOUTUBE)
                logger.info("Connected to YouTube")
        except Exception as e:
            logger.error(f"Failed to connect to YouTube: {e}")
            
    async def disconnect_all(self):
        """Disconnect from all platforms."""
        self._running = False
        
        tasks = []
        
        if self.twitch_handler:
            tasks.append(self.twitch_handler.disconnect())
            
        if self.youtube_handler:
            tasks.append(self.youtube_handler.disconnect())
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
        self.connected_platforms.clear()
        logger.info("Disconnected from all platforms")
        
    def register_message_handler(self, handler: Callable):
        """Register a handler for incoming chat messages."""
        self.message_handlers.append(handler)
        
    def register_event_handler(self, handler: Callable):
        """Register a handler for stream events."""
        self.event_handlers.append(handler)
        
    async def _on_chat_message(self, data: dict):
        """Handle incoming chat message."""
        message = data.get('message')
        platform = data.get('platform')
        
        if not message:
            return
            
        logger.debug(f"Received {platform} message from {message.user.username}: {message.content[:50]}...")
        
        # Call registered handlers
        for handler in self.message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
                
    async def _on_stream_event(self, data: dict):
        """Handle stream event."""
        event = data.get('event')
        
        if not event:
            return
            
        logger.info(f"Stream event: {event.event_type.name} on {event.platform.name}")
        
        # Call registered handlers
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
                
    async def send_message(self, platform: ChatPlatform, channel: str, message: str):
        """Send a message to a specific platform."""
        if platform == ChatPlatform.TWITCH and self.twitch_handler:
            await self.twitch_handler.send_message(channel, message)
        elif platform == ChatPlatform.YOUTUBE and self.youtube_handler:
            await self.youtube_handler.send_message(message)
        else:
            logger.warning(f"Cannot send message to {platform.name}: not connected")
            
    async def broadcast_message(self, message: str):
        """Broadcast a message to all connected platforms."""
        tasks = []
        
        if ChatPlatform.TWITCH in self.connected_platforms and self.twitch_handler:
            tasks.append(
                self.twitch_handler.send_message(self.config.TWITCH_CHANNEL_TO_JOIN, message)
            )
            
        if ChatPlatform.YOUTUBE in self.connected_platforms and self.youtube_handler:
            tasks.append(self.youtube_handler.send_message(message))
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def create_poll(self, platform: ChatPlatform, title: str, choices: list[str], duration: int = 60):
        """Create a poll on a specific platform."""
        if platform == ChatPlatform.TWITCH and self.twitch_handler:
            await self.twitch_handler.create_poll(
                self.config.TWITCH_CHANNEL_TO_JOIN,
                title,
                choices,
                duration
            )
        else:
            logger.warning(f"Polls not supported on {platform.name}")
            
    def get_connected_platforms(self) -> list[str]:
        """Get list of connected platform names."""
        return [p.name for p in self.connected_platforms]
        
    def is_connected(self, platform: ChatPlatform) -> bool:
        """Check if connected to a specific platform."""
        return platform in self.connected_platforms
        
    @property
    def total_connected_platforms(self) -> int:
        """Get number of connected platforms."""
        return len(self.connected_platforms)
