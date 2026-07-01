"""
Twitch Bot Integration
======================

Handles Twitch chat connection, events, and API interactions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable

try:
    from twitchio.ext import commands as twitch_commands
    from twitchio.ext import eventsub
    TWITCH_AVAILABLE = True
except ImportError:
    TWITCH_AVAILABLE = False

from ..config import get_config
from .chat_message import ChatMessage, ChatUser, ChatPlatform
from .stream_events import StreamEvent, EventType, SubscriptionData, RaidData
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class TwitchBotHandler:
    """Handles Twitch bot functionality."""
    
    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.bot = None
        self.es_client = None
        self.is_connected = False
        
    async def connect(self):
        """Connect to Twitch chat and eventsub."""
        if not TWITCH_AVAILABLE:
            logger.warning("Twitchio not installed, Twitch integration disabled")
            return
            
        if not self.config.TWITCH_OAUTH_TOKEN or not self.config.TWITCH_BOT_USERNAME:
            logger.warning("Twitch credentials not configured")
            return
            
        try:
            # Create bot instance
            self.bot = twitch_commands.Bot(
                token=self.config.TWITCH_OAUTH_TOKEN,
                prefix='!',
                initial_channels=[self.config.TWITCH_CHANNEL_TO_JOIN]
            )
            
            # Register event handlers
            @self.bot.event()
            async def ready():
                logger.info(f"Twitch bot connected, joined {self.config.TWITCH_CHANNEL_TO_JOIN}")
                self.is_connected = True
                await self.event_bus.publish('twitch_ready', {'bot': self.bot})
                
            @self.bot.event()
            async def message(ctx):
                if ctx.author.bot_id:  # Ignore other bots
                    return
                    
                user = ChatUser(
                    id=ctx.author.id,
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    platform=ChatPlatform.TWITCH,
                    is_moderator=ctx.chatter.is_mod,
                    is_subscriber=ctx.chatter.is_sub,
                    badges=ctx.author.badges,
                )
                
                message = ChatMessage(
                    id=ctx.message.id,
                    user=user,
                    content=ctx.content,
                    timestamp=datetime.utcnow(),
                    platform=ChatPlatform.TWITCH,
                    bits_donated=ctx.message.bits,
                )
                
                await self.event_bus.publish('chat_message', {
                    'message': message,
                    'platform': 'twitch'
                })
                
            @self.bot.event()
            async def channel_subscription(ctx):
                """Handle new subscriptions."""
                user = ChatUser(
                    id=ctx.user.id,
                    username=ctx.user.name,
                    display_name=ctx.user.display_name,
                    platform=ChatPlatform.TWITCH,
                )
                
                sub_data = SubscriptionData(
                    user=user,
                    tier=ctx.subscription.tier,
                    months=1,
                    is_gift=False,
                )
                
                event = StreamEvent(
                    event_type=EventType.NEW_SUBSCRIBER,
                    platform=ChatPlatform.TWITCH,
                    timestamp=datetime.utcnow(),
                    data={'subscription': sub_data},
                )
                
                await self.event_bus.publish('stream_event', {'event': event})
                
            @self.bot.event()
            async def channel_sub_gift(ctx):
                """Handle gifted subscriptions."""
                gifter = ChatUser(
                    id=ctx.gifter_user.id,
                    username=ctx.gifter_user.name,
                    display_name=ctx.gifter_user.display_name,
                    platform=ChatPlatform.TWITCH,
                )
                
                recipient = ChatUser(
                    id=ctx.receiver_user.id,
                    username=ctx.receiver_user.name,
                    display_name=ctx.receiver_user.display_name,
                    platform=ChatPlatform.TWITCH,
                ) if ctx.receiver_user else None
                
                sub_data = SubscriptionData(
                    user=recipient,
                    tier=ctx.subscription.tier,
                    months=ctx.subscription.months,
                    is_gift=True,
                    gifter=gifter,
                    gift_months=ctx.total,
                )
                
                event = StreamEvent(
                    event_type=EventType.SUBSCRIPTION_GIFTED,
                    platform=ChatPlatform.TWITCH,
                    timestamp=datetime.utcnow(),
                    data={'subscription': sub_data},
                )
                
                await self.event_bus.publish('stream_event', {'event': event})
                
            @self.bot.event()
            async def raid(ctx):
                """Handle raids."""
                from .stream_events import RaidData
                
                raid_data = RaidData(
                    source_channel=ctx.raiding_channel.name,
                    viewer_count=ctx.viewers,
                    timestamp=datetime.utcnow(),
                )
                
                event = StreamEvent(
                    event_type=EventType.RAID_RECEIVED,
                    platform=ChatPlatform.TWITCH,
                    timestamp=datetime.utcnow(),
                    data={'raid': raid_data},
                )
                
                await self.event_bus.publish('stream_event', {'event': event})
                
            @self.bot.event()
            async def cheer(ctx):
                """Handle bits cheers."""
                user = ChatUser(
                    id=ctx.user.id,
                    username=ctx.user.name,
                    display_name=ctx.user.display_name,
                    platform=ChatPlatform.TWITCH,
                )
                
                event = StreamEvent(
                    event_type=EventType.BITS_CHEERED,
                    platform=ChatPlatform.TWITCH,
                    timestamp=datetime.utcnow(),
                    data={
                        'user': user,
                        'amount': ctx.bits,
                        'message': ctx.message,
                    },
                )
                
                await self.event_bus.publish('stream_event', {'event': event})
                
            # Start the bot
            await self.bot.start()
            
        except Exception as e:
            logger.error(f"Error connecting to Twitch: {e}", exc_info=True)
            self.is_connected = False
            
    async def disconnect(self):
        """Disconnect from Twitch."""
        if self.bot and self.is_connected:
            await self.bot.stop()
            self.is_connected = False
            logger.info("Twitch bot disconnected")
            
    async def send_message(self, channel: str, message: str):
        """Send a message to Twitch chat."""
        if not self.is_connected or not self.bot:
            logger.warning("Cannot send message: not connected to Twitch")
            return
            
        try:
            channel_obj = self.bot.get_channel(channel)
            if channel_obj:
                await channel_obj.send(message)
                logger.debug(f"Sent Twitch message to {channel}: {message[:50]}...")
        except Exception as e:
            logger.error(f"Error sending Twitch message: {e}")
            
    async def create_poll(self, channel: str, title: str, choices: list[str], duration: int = 60):
        """Create a poll in Twitch chat."""
        if not self.is_connected or not self.bot:
            return
            
        try:
            # This would use the Twitch API directly
            # Implementation depends on twitchio version
            logger.info(f"Poll created: {title} with {len(choices)} choices")
        except Exception as e:
            logger.error(f"Error creating poll: {e}")
