"""
MyCompanion Framework - Companion State Manager

This module maintains the shared state of the AI companion, including:
- Current activity state (speaking, thinking, idle)
- Turn-taking locks
- Recent conversation history
- Active user interactions

All state changes emit signals for other modules to react to.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ActivityState(Enum):
    """Current activity state of the AI companion."""
    IDLE = "idle"                      # Doing nothing, waiting for input
    LISTENING = "listening"            # Recording/processing user speech
    THINKING = "thinking"              # Waiting for LLM response
    SPEAKING = "speaking"              # Currently talking via TTS
    PROCESSING_VISUAL = "processing_visual"  # Analyzing screen/image
    BUSY = "busy"                      # Performing a task (game interaction, etc.)


@dataclass
class ConversationTurn:
    """Represents a single turn in conversation."""
    timestamp: float
    speaker: str  # "user" or "ai"
    text: str
    emotion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "speaker": self.speaker,
            "text": self.text,
            "emotion": self.emotion,
            "metadata": self.metadata,
        }


@dataclass
class UserPresence:
    """Tracks user presence and activity."""
    is_present: bool = True
    last_interaction: float = field(default_factory=time.time)
    active_window: Optional[str] = None
    is_gaming: bool = False
    is_watching_video: bool = False
    is_listening_music: bool = False


class SignalEmitter:
    """Simple signal/slot system for state change notifications."""
    
    def __init__(self):
        self._signals: Dict[str, List[Callable]] = {}
    
    def connect(self, signal_name: str, callback: Callable):
        """Connect a callback to a signal."""
        if signal_name not in self._signals:
            self._signals[signal_name] = []
        self._signals[signal_name].append(callback)
        logger.debug(f"Connected callback to signal: {signal_name}")
    
    def disconnect(self, signal_name: str, callback: Callable):
        """Disconnect a callback from a signal."""
        if signal_name in self._signals:
            try:
                self._signals[signal_name].remove(callback)
            except ValueError:
                pass
    
    def emit(self, signal_name: str, *args, **kwargs):
        """Emit a signal with arguments."""
        if signal_name in self._signals:
            for callback in self._signals[signal_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in signal callback for {signal_name}: {e}")
    
    async def emit_async(self, signal_name: str, *args, **kwargs):
        """Emit a signal asynchronously."""
        if signal_name in self._signals:
            for callback in self._signals[signal_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in async signal callback for {signal_name}: {e}")


class CompanionState(SignalEmitter):
    """
    Central state manager for the AI companion.
    
    This class maintains all shared state and provides methods for:
    - State queries
    - State transitions
    - Conversation history management
    - Turn-taking coordination
    
    Other modules should connect to signals to react to state changes.
    
    Usage:
        state = CompanionState()
        
        # Connect to state changes
        state.connect("state_changed", on_state_changed)
        state.connect("message_received", on_message)
        
        # Update state
        await state.set_activity(ActivityState.THINKING)
        state.add_user_message("Hello!")
    """
    
    def __init__(self, max_history: int = 100):
        super().__init__()
        
        # Core state
        self.activity: ActivityState = ActivityState.IDLE
        self.user_presence = UserPresence()
        
        # Conversation management
        self.max_history = max_history
        self.conversation_history: List[ConversationTurn] = []
        self.short_term_context: List[str] = []  # Last few messages for context
        
        # Turn-taking
        self.turn_lock = asyncio.Lock()
        self.can_interrupt: bool = True  # Can user interrupt AI mid-sentence?
        self.last_ai_response_time: float = 0
        self.last_user_input_time: float = 0
        
        # Boredom tracking
        self.idle_start_time: Optional[float] = None
        self.boredom_level: float = 0.0  # 0.0 - 1.0
        
        # Session tracking
        self.session_start: float = time.time()
        self.total_messages: int = 0
        self.total_responses: int = 0
        
        # Custom state storage
        self.custom_state: Dict[str, Any] = {}
        
        logger.info("CompanionState initialized")
    
    # =========================================================================
    # ACTIVITY STATE MANAGEMENT
    # =========================================================================
    
    async def set_activity(self, new_activity: ActivityState, reason: str = ""):
        """
        Change the current activity state.
        
        Args:
            new_activity: The new activity state
            reason: Optional reason for the change (for logging)
        """
        old_activity = self.activity
        self.activity = new_activity
        
        logger.debug(f"Activity changed: {old_activity.value} -> {new_activity.value} ({reason})")
        
        # Emit signal
        await self.emit_async(
            "state_changed",
            old_activity,
            new_activity,
            reason
        )
        
        # Track idle time
        if new_activity == ActivityState.IDLE:
            self.idle_start_time = time.time()
        else:
            if self.idle_start_time:
                idle_duration = time.time() - self.idle_start_time
                await self.emit_async("idle_ended", idle_duration)
            self.idle_start_time = None
    
    def is_available(self) -> bool:
        """Check if AI is available for new input."""
        return self.activity in [ActivityState.IDLE, ActivityState.LISTENING]
    
    def is_busy(self) -> bool:
        """Check if AI is currently busy."""
        return self.activity in [ActivityState.SPEAKING, ActivityState.THINKING, ActivityState.BUSY]
    
    # =========================================================================
    # CONVERSATION HISTORY
    # =========================================================================
    
    def add_user_message(self, text: str, emotion: str = None, metadata: dict = None):
        """Add a user message to conversation history."""
        turn = ConversationTurn(
            timestamp=time.time(),
            speaker="user",
            text=text,
            emotion=emotion,
            metadata=metadata or {},
        )
        self._add_turn(turn)
        self.last_user_input_time = time.time()
        self.total_messages += 1
        
        logger.debug(f"User message added: '{text[:50]}...'")
        return turn
    
    def add_ai_message(self, text: str, emotion: str = None, metadata: dict = None):
        """Add an AI response to conversation history."""
        turn = ConversationTurn(
            timestamp=time.time(),
            speaker="ai",
            text=text,
            emotion=emotion,
            metadata=metadata or {},
        )
        self._add_turn(turn)
        self.last_ai_response_time = time.time()
        self.total_responses += 1
        
        logger.debug(f"AI message added: '{text[:50]}...'")
        return turn
    
    def _add_turn(self, turn: ConversationTurn):
        """Internal method to add a turn and maintain history size."""
        self.conversation_history.append(turn)
        
        # Trim history if too long
        while len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
        
        # Update short-term context (last 10 turns)
        self.short_term_context = [
            f"{t.speaker}: {t.text}" 
            for t in self.conversation_history[-10:]
        ]
        
        # Emit signal
        asyncio.create_task(self.emit_async("message_added", turn))
    
    def get_recent_messages(self, count: int = 10) -> List[ConversationTurn]:
        """Get the most recent conversation turns."""
        return self.conversation_history[-count:]
    
    def get_context_string(self, max_turns: int = 20) -> str:
        """
        Get conversation history as a formatted string for LLM context.
        
        Args:
            max_turns: Maximum number of turns to include
        
        Returns:
            Formatted conversation history
        """
        turns = self.conversation_history[-max_turns:]
        lines = []
        for turn in turns:
            speaker_label = "You" if turn.speaker == "user" else "Assistant"
            lines.append(f"{speaker_label}: {turn.text}")
        return "\n".join(lines)
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        self.short_term_context.clear()
        logger.info("Conversation history cleared")
        asyncio.create_task(self.emit_async("history_cleared"))
    
    # =========================================================================
    # TURN-TAKING COORDINATION
    # =========================================================================
    
    async def acquire_turn(self, timeout: float = 30.0) -> bool:
        """
        Acquire the turn lock to speak/respond.
        
        Args:
            timeout: Maximum time to wait for lock
        
        Returns:
            True if lock acquired, False if timed out
        """
        try:
            acquired = await asyncio.wait_for(self.turn_lock.acquire(), timeout=timeout)
            if acquired:
                logger.debug("Turn lock acquired")
            return acquired
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for turn lock")
            return False
    
    def release_turn(self):
        """Release the turn lock."""
        if self.turn_lock.locked():
            self.turn_lock.release()
            logger.debug("Turn lock released")
    
    async def start_thinking(self):
        """Mark that AI is starting to think."""
        await self.set_activity(ActivityState.THINKING, "Processing input")
    
    async def start_speaking(self):
        """Mark that AI is starting to speak."""
        await self.set_activity(ActivityState.SPEAKING, "TTS playback")
    
    async def finish_speaking(self):
        """Mark that AI finished speaking."""
        await self.set_activity(ActivityState.IDLE, "Finished speaking")
    
    # =========================================================================
    # BOREDOM TRACKING
    # =========================================================================
    
    def get_idle_duration(self) -> float:
        """Get duration of current idle period in seconds."""
        if self.idle_start_time is None:
            return 0.0
        return time.time() - self.idle_start_time
    
    def update_boredom(self, boredom_threshold: float = 60.0):
        """
        Update boredom level based on idle time.
        
        Args:
            boredom_threshold: Seconds of idle time to reach max boredom
        
        Returns:
            Current boredom level (0.0 - 1.0)
        """
        idle_duration = self.get_idle_duration()
        
        # Linear increase up to threshold
        self.boredom_level = min(1.0, idle_duration / boredom_threshold)
        
        return self.boredom_level
    
    def reset_boredom(self):
        """Reset boredom level (called on user interaction)."""
        self.boredom_level = 0.0
        self.idle_start_time = None
        logger.debug("Boredom reset")
    
    # =========================================================================
    # USER PRESENCE TRACKING
    # =========================================================================
    
    def update_user_presence(self, is_present: bool = True, active_window: str = None):
        """Update user presence information."""
        self.user_presence.is_present = is_present
        self.user_presence.last_interaction = time.time()
        
        if active_window:
            self.user_presence.active_window = active_window
            self._detect_activity_type(active_window)
        
        asyncio.create_task(self.emit_async("user_presence_updated", self.user_presence))
    
    def _detect_activity_type(self, window_title: str):
        """Detect what the user is doing based on active window."""
        window_lower = window_title.lower()
        
        # Gaming detection
        game_keywords = ["game", "steam", "epic", "origin", "league", "valorant", "minecraft"]
        self.user_presence.is_gaming = any(kw in window_lower for kw in game_keywords)
        
        # Video detection
        video_keywords = ["youtube", "netflix", "vlc", "mpv", "prime", "tiktok"]
        self.user_presence.is_watching_video = any(kw in window_lower for kw in video_keywords)
        
        # Music detection
        music_keywords = ["spotify", "music", "soundcloud", "itunes", "apple music"]
        self.user_presence.is_listening_music = any(kw in window_lower for kw in music_keywords)
    
    # =========================================================================
    # CUSTOM STATE
    # =========================================================================
    
    def set_custom_state(self, key: str, value: Any):
        """Set a custom state value."""
        old_value = self.custom_state.get(key)
        self.custom_state[key] = value
        logger.debug(f"Custom state: {key} = {value}")
        asyncio.create_task(self.emit_async(f"custom_state:{key}", old_value, value))
    
    def get_custom_state(self, key: str, default: Any = None) -> Any:
        """Get a custom state value."""
        return self.custom_state.get(key, default)
    
    # =========================================================================
    # STATISTICS & SERIALIZATION
    # =========================================================================
    
    def get_statistics(self) -> dict:
        """Get session statistics."""
        session_duration = time.time() - self.session_start
        
        return {
            "session_duration_seconds": session_duration,
            "total_messages": self.total_messages,
            "total_responses": self.total_responses,
            "current_activity": self.activity.value,
            "boredom_level": self.boredom_level,
            "conversation_turns": len(self.conversation_history),
            "user_is_present": self.user_presence.is_present,
            "user_activity": {
                "gaming": self.user_presence.is_gaming,
                "watching_video": self.user_presence.is_watching_video,
                "listening_music": self.user_presence.is_listening_music,
            }
        }
    
    def to_dict(self) -> dict:
        """Serialize state to dictionary."""
        return {
            "activity": self.activity.value,
            "user_presence": {
                "is_present": self.user_presence.is_present,
                "last_interaction": self.user_presence.last_interaction,
                "active_window": self.user_presence.active_window,
            },
            "conversation_history": [t.to_dict() for t in self.conversation_history[-50:]],
            "boredom_level": self.boredom_level,
            "statistics": self.get_statistics(),
            "custom_state": self.custom_state,
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return (
            f"CompanionState(activity={self.activity.value}, "
            f"messages={len(self.conversation_history)}, "
            f"boredom={self.boredom_level:.2f})"
        )


# =============================================================================
# GLOBAL STATE INSTANCE
# =============================================================================

# Global state instance (lazy-loaded)
_global_state: Optional[CompanionState] = None


def get_state() -> CompanionState:
    """Get or create the global state instance."""
    global _global_state
    if _global_state is None:
        _global_state = CompanionState()
    return _global_state


def reset_state():
    """Reset the global state instance."""
    global _global_state
    _global_state = CompanionState()
    logger.info("Global state reset")
