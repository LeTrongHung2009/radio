"""
Chat Message Data Models
=========================

Defines data structures for chat messages from various streaming platforms.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class ChatPlatform(Enum):
    """Supported streaming platforms."""
    TWITCH = auto()
    YOUTUBE = auto()
    DISCORD = auto()
    CUSTOM = auto()


@dataclass
class ChatUser:
    """Represents a user in chat."""
    id: str
    username: str
    display_name: str
    platform: ChatPlatform
    is_moderator: bool = False
    is_subscriber: bool = False
    is_vip: bool = False
    badges: list[str] = field(default_factory=list)
    color: Optional[str] = None
    follower_since: Optional[datetime] = None
    subscriber_months: int = 0
    
    def __hash__(self):
        return hash((self.id, self.platform))
    
    def __eq__(self, other):
        if not isinstance(other, ChatUser):
            return False
        return self.id == other.id and self.platform == other.platform


@dataclass
class ChatMessage:
    """Represents a chat message from any platform."""
    id: str
    user: ChatUser
    content: str
    timestamp: datetime
    platform: ChatPlatform
    is_action: bool = False  # /me action
    is_first_message: bool = False
    reply_to: Optional[str] = None  # ID of message being replied to
    mentions: list[str] = field(default_factory=list)
    emotes: list[dict] = field(default_factory=list)
    bits_donated: int = 0
    channel_points: int = 0
    redemption_id: Optional[str] = None
    raw_data: dict = field(default_factory=dict)
    
    @property
    def is_from_known_user(self) -> bool:
        """Check if this user has been seen before."""
        return self.user.follower_since is not None or self.user.subscriber_months > 0
    
    @property
    def importance_score(self) -> float:
        """Calculate message importance for prioritization."""
        score = 1.0
        
        if self.user.is_moderator:
            score += 3.0
        if self.user.is_vip:
            score += 2.0
        if self.user.is_subscriber:
            score += min(2.0, self.user.subscriber_months / 6.0)
        if self.bits_donated > 0:
            score += min(3.0, self.bits_donated / 100.0)
        if self.is_first_message:
            score += 2.0
        if len(self.mentions) > 0:
            score += 1.0
            
        return score
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'user_id': self.user.id,
            'username': self.user.username,
            'display_name': self.user.display_name,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'platform': self.platform.name,
            'is_action': self.is_action,
            'is_first_message': self.is_first_message,
            'reply_to': self.reply_to,
            'mentions': self.mentions,
            'bits_donated': self.bits_donated,
            'channel_points': self.channel_points,
            'importance_score': self.importance_score,
        }
