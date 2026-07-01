"""
Game State Data Models
======================

Defines data structures for game state and actions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Any

from companion.utils.serialization import dataclass_to_dict


class GameEventType(Enum):
    """Types of game events."""
    # General events
    GAME_STARTED = auto()
    GAME_ENDED = auto()
    GAME_PAUSED = auto()
    GAME_RESUMED = auto()
    
    # Action events
    ACTION_EXECUTED = auto()
    ACTION_FAILED = auto()
    
    # State change events
    STATE_CHANGED = auto()
    LOCATION_CHANGED = auto()
    INVENTORY_CHANGED = auto()
    
    # Battle events (for RPGs)
    BATTLE_STARTED = auto()
    BATTLE_ENDED = auto()
    POKEMON_CAUGHT = auto()
    POKEMON_FAINTED = auto()
    LEVEL_UP = auto()
    
    # Chess events
    MOVE_MADE = auto()
    CHECK = auto()
    CHECKMATE = auto()
    RESIGNATION = auto()


class GameAction(Enum):
    """Generic game actions."""
    # Movement
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    
    # Interaction
    INTERACT = auto()
    TALK = auto()
    PICKUP = auto()
    USE_ITEM = auto()
    
    # Menu actions
    OPEN_MENU = auto()
    SELECT = auto()
    BACK = auto()
    
    # Battle actions
    ATTACK = auto()
    DEFEND = auto()
    RUN = auto()
    SWITCH_POKEMON = auto()
    
    # Chess actions
    CHESS_MOVE = auto()
    CHESS_RESIGN = auto()
    CHESS_DRAW_OFFER = auto()


@dataclass
class GameState:
    """Represents the current state of a game."""
    game_id: str
    game_name: str
    is_active: bool = False
    is_paused: bool = False
    current_location: Optional[str] = None
    current_objective: Optional[str] = None
    inventory: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    last_action: Optional[GameAction] = None
    last_action_time: Optional[datetime] = None
    session_start: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Pokemon-specific fields
    party: list[dict] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    
    # Chess-specific fields
    chess_board: Optional[str] = None  # FEN notation
    chess_opponent: Optional[str] = None
    chess_eval: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return dataclass_to_dict(self, [
            'game_id', 'game_name', 'is_active', 'is_paused',
            'current_location', 'current_objective', 'inventory', 'stats',
            'last_action', 'last_action_time', 'session_start',
            'party', 'badges', 'chess_board', 'chess_opponent', 'chess_eval',
        ])
        
    @property
    def playtime_seconds(self) -> int:
        """Get total playtime in seconds."""
        if not self.session_start:
            return 0
        delta = datetime.utcnow() - self.session_start
        return int(delta.total_seconds())
        
    @property
    def playtime_formatted(self) -> str:
        """Get formatted playtime string."""
        seconds = self.playtime_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class GameEvent:
    """Represents a game event."""
    event_type: GameEventType
    game_id: str
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return dataclass_to_dict(self, [
            'event_type', 'game_id', 'timestamp', 'data',
        ])
