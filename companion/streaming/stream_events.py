"""
Stream Events Module
=====================

Defines event types for streaming platform interactions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Any

from .chat_message import ChatMessage, ChatUser, ChatPlatform


class EventType(Enum):
    """Types of stream events."""
    # Chat events
    MESSAGE_RECEIVED = auto()
    MESSAGE_DELETED = auto()
    USER_TIMEOUT = auto()
    USER_BANNED = auto()
    
    # Follow/Subscribe events
    NEW_FOLLOWER = auto()
    NEW_SUBSCRIBER = auto()
    SUBSCRIPTION_GIFTED = auto()
    RESUBSCRIPTION = auto()
    
    # Donation events
    BITS_CHEERED = auto()
    DONATION_RECEIVED = auto()
    CHANNEL_POINTS_REDEMPTION = auto()
    
    # Raid/Host events
    RAID_RECEIVED = auto()
    HOST_RECEIVED = auto()
    
    # Stream state events
    STREAM_STARTED = auto()
    STREAM_ENDED = auto()
    STREAM_PAUSED = auto()
    STREAM_RESUMED = auto()
    
    # Platform specific
    TWITCH_POLL_CREATED = auto()
    TWITCH_POLL_VOTED = auto()
    TWITCH_PREDICTION_CREATED = auto()
    TWITCH_PREDICTION_RESULT = auto()
    YOUTUBE_SUPERCHAT = auto()
    YOUTUBE_MEMBER_JOIN = auto()


@dataclass
class StreamEvent:
    """Represents any event from a streaming platform."""
    event_type: EventType
    platform: ChatPlatform
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)
    
    # Convenience properties for common event data
    @property
    def user(self) -> Optional[ChatUser]:
        """Get the user associated with this event if present."""
        return self.data.get('user')
    
    @property
    def message(self) -> Optional[ChatMessage]:
        """Get the chat message if this is a message event."""
        return self.data.get('message')
    
    @property
    def amount(self) -> Optional[int]:
        """Get donation/bits amount if applicable."""
        return self.data.get('amount')
    
    @property
    def gift_count(self) -> int:
        """Get number of gifts if applicable."""
        return self.data.get('gift_count', 0)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            'event_type': self.event_type.name,
            'platform': self.platform.name,
            'timestamp': self.timestamp.isoformat(),
            'data': {},
        }
        
        # Serialize data safely
        for key, value in self.data.items():
            if isinstance(value, (ChatUser, ChatMessage)):
                result['data'][key] = value.to_dict()
            elif isinstance(value, (str, int, float, bool, list, dict)):
                result['data'][key] = value
                
        return result


@dataclass
class RaidData:
    """Data for raid events."""
    source_channel: str
    viewer_count: int
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            'source_channel': self.source_channel,
            'viewer_count': self.viewer_count,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class SubscriptionData:
    """Data for subscription events."""
    user: ChatUser
    tier: str  # "1000", "2000", "3000" for Twitch tiers
    months: int
    is_gift: bool = False
    gifter: Optional[ChatUser] = None
    gift_months: int = 0
    
    def to_dict(self) -> dict:
        return {
            'user': self.user.to_dict(),
            'tier': self.tier,
            'months': self.months,
            'is_gift': self.is_gift,
            'gifter': self.gifter.to_dict() if self.gifter else None,
            'gift_months': self.gift_months,
        }
