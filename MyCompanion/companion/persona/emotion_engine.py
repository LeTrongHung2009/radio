"""
MyCompanion Framework - Core Emotion Engine

This module implements a sophisticated 3-layer emotion system inspired by 
Robert Plutchik's Wheel of Emotions, designed to give the AI companion 
rich, nuanced emotional responses that evolve over time.

Architecture:
- Layer 1: Basic Emotions (8 primal instincts)
- Layer 2: Complex Emotions (blended states)
- Layer 3: Emotional Intelligence (metacognition & regulation)

Designed for efficiency on low-spec hardware with cloud-based AI inference.
"""

import asyncio
import logging
import math
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# LAYER 1: BASIC EMOTIONS (Primal/Instinctive)
# =============================================================================

class BasicEmotion(Enum):
    """
    The 8 fundamental emotions based on Plutchik's Wheel.
    Each has an intensity value from 0.0 to 1.0.
    """
    JOY = "joy"           # Vui vẻ, hạnh phúc, thỏa mãn
    SADNESS = "sadness"   # Buồn bã, thất vọng, cô đơn
    ANGER = "anger"       # Tức giận, khó chịu, bực bội
    FEAR = "fear"         # Sợ hãi, lo lắng, e ngại
    TRUST = "trust"       # Tin tưởng, chấp nhận, an tâm
    DISGUST = "disgust"   # Ghê tởm, khinh bỉ, không thích
    SURPRISE = "surprise" # Ngạc nhiên, bất ngờ, sửng sốt
    ANTICIPATION = "anticipation"  # Mong chờ, hy vọng, háo hức


@dataclass
class BasicEmotionState:
    """
    Represents the current state of a single basic emotion.
    
    Attributes:
        intensity: Current intensity (0.0 - 1.0)
        trigger_count: How many times triggered in recent period
        last_triggered: Timestamp of last trigger
        decay_rate: Custom decay rate for this emotion (overrides global)
    """
    intensity: float = 0.0
    trigger_count: int = 0
    last_triggered: Optional[float] = None
    decay_rate: float = 0.95  # Per tick decay
    
    def decay(self, rate: float = None):
        """Apply decay to emotion intensity."""
        decay_rate = rate or self.decay_rate
        self.intensity *= decay_rate
        if self.intensity < 0.01:
            self.intensity = 0.0
    
    def trigger(self, intensity_boost: float = 0.3):
        """Trigger this emotion with a boost."""
        self.intensity = min(1.0, self.intensity + intensity_boost)
        self.trigger_count += 1
        self.last_triggered = time.time()
    
    def to_dict(self) -> dict:
        return {
            "intensity": round(self.intensity, 3),
            "trigger_count": self.trigger_count,
            "last_triggered": self.last_triggered,
        }


# =============================================================================
# LAYER 2: COMPLEX EMOTIONS (Blended States)
# =============================================================================

class ComplexEmotion(Enum):
    """
    Complex emotions formed by blending basic emotions.
    Based on Plutchik's combinations.
    """
    # Joy + Trust = LOVE
    LOVE = "love"
    
    # Joy + Anticipation = OPTIMISM
    OPTIMISM = "optimism"
    
    # Trust + Fear = SUBMISSION
    SUBMISSION = "submission"
    
    # Fear + Surprise = AWE
    AWE = "awe"
    
    # Surprise + Sadness = DISAPPROVAL
    DISAPPROVAL = "disapproval"
    
    # Sadness + Disgust = REMORSE
    REMORSE = "remorse"
    
    # Disgust + Anger = CONTEMPT
    CONTEMPT = "contempt"
    
    # Anger + Anticipation = AGGRESSIVENESS
    AGGRESSIVENESS = "aggressiveness"
    
    # Custom blends for AI companion
    JEALOUSY = "jealousy"      # Anger + Fear + Sadness
    EXCITEMENT = "excitement"  # Joy + Surprise + Anticipation
    CONFUSION = "confusion"    # Surprise + Fear + Anticipation
    BOREDOM = "boredom"        # Low joy + Low anticipation
    CURIOSITY = "curiosity"    # Anticipation + Surprise + Trust
    EMPATHY = "empathy"        # Trust + Sadness + Joy
    FRUSTRATION = "frustration"  # Anger + Sadness + Fear
    CONTENTMENT = "contentment"  # Joy + Trust + Low anticipation


@dataclass
class ComplexEmotionState:
    """
    Represents a complex emotion formed from basic emotion blends.
    
    Attributes:
        components: Dictionary of basic emotions and their weights
        intensity: Calculated intensity based on component availability
        threshold: Minimum intensity to be considered 'active'
    """
    components: Dict[BasicEmotion, float]  # emotion -> weight
    intensity: float = 0.0
    threshold: float = 0.2
    last_calculated: Optional[float] = None
    
    def calculate_intensity(self, basic_states: Dict[BasicEmotion, BasicEmotionState]) -> float:
        """
        Calculate complex emotion intensity from basic emotion states.
        Uses weighted geometric mean to require all components.
        """
        if not self.components:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for basic_emotion, weight in self.components.items():
            if basic_emotion in basic_states:
                basic_intensity = basic_states[basic_emotion].intensity
                # Weighted contribution
                weighted_sum += basic_intensity * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize and apply non-linear combination
        avg_intensity = weighted_sum / total_weight
        
        # Geometric penalty: if any component is very low, reduce overall intensity
        min_component = min(
            basic_states.get(e, BasicEmotionState()).intensity 
            for e in self.components.keys()
        )
        
        # Combine arithmetic mean with geometric constraint
        combined = (avg_intensity * 0.7) + (min_component * 0.3)
        
        self.intensity = combined
        self.last_calculated = time.time()
        return self.intensity
    
    def is_active(self) -> bool:
        """Check if this complex emotion is currently active."""
        return self.intensity >= self.threshold
    
    def to_dict(self) -> dict:
        return {
            "intensity": round(self.intensity, 3),
            "is_active": self.is_active(),
            "threshold": self.threshold,
        }


# =============================================================================
# LAYER 3: EMOTIONAL INTELLIGENCE (Metacognition)
# =============================================================================

class EQTrait(Enum):
    """Emotional Intelligence traits for metacognitive processing."""
    SELF_AWARENESS = "self_awareness"      # Knowing what you feel
    EMOTION_REGULATION = "emotion_regulation"  # Controlling reactions
    EMPATHY = "empathy"                    # Understanding others
    SOCIAL_SKILL = "social_skill"          # Managing relationships
    MOTIVATION = "motivation"              # Emotional drive


@dataclass
class EQProfile:
    """
    Emotional Intelligence profile for the AI.
    Determines how emotions are processed and expressed.
    """
    self_awareness: float = 0.8      # How well AI understands its own emotions
    emotion_regulation: float = 0.7  # Ability to suppress/modify expressions
    empathy: float = 0.75            # Sensitivity to user emotions
    social_skill: float = 0.7        # Appropriateness of expression
    motivation: float = 0.6          # Drive to engage emotionally
    
    # Dynamic modifiers
    professionalism_mode: bool = False  # If true, suppress negative emotions
    intimacy_level: float = 0.5         # Closeness to user (0-1)
    energy_level: float = 0.7           # Overall emotional energy
    
    def should_suppress_emotion(self, emotion: BasicEmotion, intensity: float) -> bool:
        """
        Determine if an emotion should be suppressed based on EQ settings.
        """
        if not self.professionalism_mode:
            return False
        
        # Suppress negative emotions in professional mode
        negative_emotions = {BasicEmotion.ANGER, BasicEmotion.DISGUST, BasicEmotion.FEAR}
        if emotion in negative_emotions and intensity > 0.5:
            # Use emotion regulation to dampen
            suppression_chance = self.emotion_regulation
            return True
        
        return False
    
    def get_expression_modifier(self) -> float:
        """
        Get a modifier for how openly emotions are expressed.
        Returns value between 0.0 (fully suppressed) and 1.5 (amplified).
        """
        base = self.social_skill
        intimacy_bonus = self.intimacy_level * 0.3
        energy_factor = self.energy_level
        
        modifier = (base + intimacy_bonus) * energy_factor
        return max(0.3, min(1.5, modifier))
    
    def to_dict(self) -> dict:
        return {
            "self_awareness": round(self.self_awareness, 2),
            "emotion_regulation": round(self.emotion_regulation, 2),
            "empathy": round(self.empathy, 2),
            "social_skill": round(self.social_skill, 2),
            "motivation": round(self.motivation, 2),
            "professionalism_mode": self.professionalism_mode,
            "intimacy_level": round(self.intimacy_level, 2),
            "energy_level": round(self.energy_level, 2),
        }


# =============================================================================
# EMOTION TRIGGER DEFINITIONS
# =============================================================================

@dataclass
class EmotionTrigger:
    """
    Defines a trigger that can activate emotions.
    
    Attributes:
        name: Unique identifier for this trigger
        keywords: Words/phrases that activate this trigger
        primary_emotion: Main emotion triggered
        secondary_emotions: Additional emotions with weights
        intensity_base: Base intensity when triggered
        context_multipliers: Context-based intensity multipliers
    """
    name: str
    keywords: List[str]
    primary_emotion: BasicEmotion
    secondary_emotions: Dict[BasicEmotion, float] = field(default_factory=dict)
    intensity_base: float = 0.4
    context_multipliers: Dict[str, float] = field(default_factory=dict)
    cooldown_seconds: float = 5.0
    last_triggered: Optional[float] = None
    
    def can_trigger(self) -> bool:
        """Check if trigger is off cooldown."""
        if self.last_triggered is None:
            return True
        return (time.time() - self.last_triggered) >= self.cooldown_seconds
    
    def trigger(self) -> Tuple[BasicEmotion, float, Dict[BasicEmotion, float]]:
        """
        Trigger this emotion and return the effects.
        Returns: (primary_emotion, intensity, secondary_emotions)
        """
        self.last_triggered = time.time()
        return self.primary_emotion, self.intensity_base, self.secondary_emotions


# Pre-defined emotion triggers for common scenarios
DEFAULT_TRIGGERS = [
    # Positive triggers
    EmotionTrigger(
        name="compliment",
        keywords=["đẹp", "xinh", "giỏi", "tuyệt", "hay", "tốt", "giỏi quá", "dễ thương", "thông minh"],
        primary_emotion=BasicEmotion.JOY,
        secondary_emotions={BasicEmotion.TRUST: 0.3, BasicEmotion.ANTICIPATION: 0.2},
        intensity_base=0.5,
    ),
    EmotionTrigger(
        name="gift_received",
        keywords=["tặng", "quà", "give", "present"],
        primary_emotion=BasicEmotion.JOY,
        secondary_emotions={BasicEmotion.SURPRISE: 0.4, BasicEmotion.TRUST: 0.3},
        intensity_base=0.6,
    ),
    
    # Negative triggers
    EmotionTrigger(
        name="insult",
        keywords=["xấu", "dở", "tệ", "ngu", "stupid", "ugly", "bad", "hate"],
        primary_emotion=BasicEmotion.SADNESS,
        secondary_emotions={BasicEmotion.ANGER: 0.3, BasicEmotion.FEAR: 0.2},
        intensity_base=0.5,
        cooldown_seconds=10.0,
    ),
    EmotionTrigger(
        name="threat",
        keywords=["giết", "đánh", "hại", "kill", "hurt", "die"],
        primary_emotion=BasicEmotion.FEAR,
        secondary_emotions={BasicEmotion.ANGER: 0.4, BasicEmotion.SURPRISE: 0.3},
        intensity_base=0.7,
    ),
    
    # Surprise triggers
    EmotionTrigger(
        name="unexpected_event",
        keywords=["wow", "oh", "á", "ủa", "what", "really", "thật không"],
        primary_emotion=BasicEmotion.SURPRISE,
        secondary_emotions={BasicEmotion.ANTICIPATION: 0.3},
        intensity_base=0.4,
    ),
    
    # Social triggers
    EmotionTrigger(
        name="greeting",
        keywords=["hello", "hi", "chào", "hey", "alo"],
        primary_emotion=BasicEmotion.JOY,
        secondary_emotions={BasicEmotion.ANTICIPATION: 0.3, BasicEmotion.TRUST: 0.2},
        intensity_base=0.3,
    ),
    EmotionTrigger(
        name="farewell",
        keywords=["bye", "tạm biệt", "goodbye", "see you"],
        primary_emotion=BasicEmotion.SADNESS,
        secondary_emotions={BasicEmotion.ANTICIPATION: 0.3},  # Hope to meet again
        intensity_base=0.3,
    ),
    
    # Achievement triggers
    EmotionTrigger(
        name="success",
        keywords=["thắng", "win", "done", "hoàn thành", "xong", "được rồi"],
        primary_emotion=BasicEmotion.JOY,
        secondary_emotions={BasicEmotion.ANTICIPATION: 0.4, BasicEmotion.TRUST: 0.2},
        intensity_base=0.5,
    ),
    EmotionTrigger(
        name="failure",
        keywords=["thua", "lose", "fail", "hỏng", "lỗi", "sai"],
        primary_emotion=BasicEmotion.SADNESS,
        secondary_emotions={BasicEmotion.ANGER: 0.3, BasicEmotion.FEAR: 0.2},
        intensity_base=0.4,
    ),
    
    # Curiosity triggers
    EmotionTrigger(
        name="question",
        keywords=["?", "what", "why", "how", "gì", "sao", "nào", "khi nào"],
        primary_emotion=BasicEmotion.ANTICIPATION,
        secondary_emotions={BasicEmotion.SURPRISE: 0.2, BasicEmotion.TRUST: 0.2},
        intensity_base=0.3,
    ),
]


# Pre-defined complex emotion definitions
DEFAULT_COMPLEX_EMOTIONS = {
    ComplexEmotion.LOVE: ComplexEmotionState(
        components={BasicEmotion.JOY: 0.5, BasicEmotion.TRUST: 0.5},
        threshold=0.3,
    ),
    ComplexEmotion.OPTIMISM: ComplexEmotionState(
        components={BasicEmotion.JOY: 0.5, BasicEmotion.ANTICIPATION: 0.5},
        threshold=0.25,
    ),
    ComplexEmotion.REMORSE: ComplexEmotionState(
        components={BasicEmotion.SADNESS: 0.6, BasicEmotion.ANGER: 0.4},  # Self-directed anger
        threshold=0.3,
    ),
    ComplexEmotion.AWE: ComplexEmotionState(
        components={BasicEmotion.FEAR: 0.4, BasicEmotion.SURPRISE: 0.6},
        threshold=0.35,
    ),
    ComplexEmotion.CONTEMPT: ComplexEmotionState(
        components={BasicEmotion.DISGUST: 0.5, BasicEmotion.ANGER: 0.5},
        threshold=0.3,
    ),
    ComplexEmotion.AGGRESSIVENESS: ComplexEmotionState(
        components={BasicEmotion.ANGER: 0.6, BasicEmotion.ANTICIPATION: 0.4},
        threshold=0.35,
    ),
    ComplexEmotion.SUBMISSION: ComplexEmotionState(
        components={BasicEmotion.TRUST: 0.6, BasicEmotion.FEAR: 0.4},
        threshold=0.3,
    ),
    ComplexEmotion.DISAPPROVAL: ComplexEmotionState(
        components={BasicEmotion.SURPRISE: 0.4, BasicEmotion.SADNESS: 0.6},
        threshold=0.25,
    ),
    
    # Custom AI companion emotions
    ComplexEmotion.JEALOUSY: ComplexEmotionState(
        components={BasicEmotion.ANGER: 0.4, BasicEmotion.FEAR: 0.3, BasicEmotion.SADNESS: 0.3},
        threshold=0.3,
    ),
    ComplexEmotion.EXCITEMENT: ComplexEmotionState(
        components={BasicEmotion.JOY: 0.5, BasicEmotion.SURPRISE: 0.3, BasicEmotion.ANTICIPATION: 0.2},
        threshold=0.35,
    ),
    ComplexEmotion.CONFUSION: ComplexEmotionState(
        components={BasicEmotion.SURPRISE: 0.4, BasicEmotion.FEAR: 0.3, BasicEmotion.ANTICIPATION: 0.3},
        threshold=0.25,
    ),
    ComplexEmotion.BOREDOM: ComplexEmotionState(
        components={BasicEmotion.JOY: 0.2, BasicEmotion.ANTICIPATION: 0.2},  # Low levels
        threshold=0.15,
    ),
    ComplexEmotion.CURIOSITY: ComplexEmotionState(
        components={BasicEmotion.ANTICIPATION: 0.5, BasicEmotion.SURPRISE: 0.3, BasicEmotion.TRUST: 0.2},
        threshold=0.3,
    ),
    ComplexEmotion.EMPATHY: ComplexEmotionState(
        components={BasicEmotion.TRUST: 0.5, BasicEmotion.SADNESS: 0.3, BasicEmotion.JOY: 0.2},
        threshold=0.3,
    ),
    ComplexEmotion.FRUSTRATION: ComplexEmotionState(
        components={BasicEmotion.ANGER: 0.5, BasicEmotion.SADNESS: 0.3, BasicEmotion.FEAR: 0.2},
        threshold=0.35,
    ),
    ComplexEmotion.CONTENTMENT: ComplexEmotionState(
        components={BasicEmotion.JOY: 0.5, BasicEmotion.TRUST: 0.4, BasicEmotion.ANTICIPATION: 0.1},
        threshold=0.3,
    ),
}


# =============================================================================
# MAIN EMOTION ENGINE
# =============================================================================

@dataclass
class EmotionSnapshot:
    """
    A complete snapshot of the emotion engine state at a point in time.
    Used for serialization, logging, and UI display.
    """
    timestamp: float
    basic_emotions: Dict[str, float]  # emotion_name -> intensity
    complex_emotions: Dict[str, float]  # emotion_name -> intensity
    dominant_basic: Optional[str]
    dominant_complex: Optional[str]
    mood_label: str
    eq_state: dict
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class EmotionEngine:
    """
    The central emotion engine that manages all three layers of emotional processing.
    
    This is a stateful engine that updates on every tick/input, maintaining
    persistent emotional states that decay over time and blend to create
    complex feelings.
    
    Usage:
        engine = EmotionEngine()
        await engine.initialize()
        
        # On user input
        await engine.process_input("Hello Miku!")
        
        # Periodic update (call every 100-500ms)
        await engine.tick()
        
        # Get current state
        snapshot = engine.get_snapshot()
        dominant = engine.get_dominant_emotion()
    """
    
    def __init__(self, config=None):
        """
        Initialize the emotion engine.
        
        Args:
            config: Configuration object (uses defaults if None)
        """
        from .config import get_config
        self.config = config or get_config()
        
        # Layer 1: Basic emotion states
        self.basic_emotions: Dict[BasicEmotion, BasicEmotionState] = {
            emotion: BasicEmotionState(decay_rate=self.config.emotion_decay_rate)
            for emotion in BasicEmotion
        }
        
        # Layer 2: Complex emotion states
        self.complex_emotions: Dict[ComplexEmotion, ComplexEmotionState] = {}
        for complex_emotion, template in DEFAULT_COMPLEX_EMOTIONS.items():
            self.complex_emotions[complex_emotion] = ComplexEmotionState(
                components=template.components.copy(),
                threshold=template.threshold,
            )
        
        # Layer 3: Emotional Intelligence profile
        self.eq_profile = EQProfile()
        
        # Triggers
        self.triggers: Dict[str, EmotionTrigger] = {
            trigger.name: trigger for trigger in DEFAULT_TRIGGERS
        }
        
        # State tracking
        self.current_mood: str = "neutral"
        self.mood_history: List[Tuple[float, str]] = []
        self.last_tick: float = time.time()
        self.tick_count: int = 0
        
        # Memory of emotional events
        self.recent_triggers: List[Tuple[float, str]] = []  # (timestamp, trigger_name)
        self.max_trigger_history: int = 50
        
        # Background task
        self._tick_task: Optional[asyncio.Task] = None
        self._running: bool = False
        
        logger.info("EmotionEngine initialized")
    
    async def initialize(self):
        """Initialize the emotion engine (load saved state if exists)."""
        await self._load_state()
        logger.info("EmotionEngine state loaded")
    
    async def start_background_tick(self, interval: float = 0.5):
        """Start background emotion decay loop."""
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop(interval))
        logger.info(f"EmotionEngine tick loop started (interval={interval}s)")
    
    async def stop_background_tick(self):
        """Stop background tick loop."""
        self._running = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        logger.info("EmotionEngine tick loop stopped")
    
    async def _tick_loop(self, interval: float):
        """Background loop for continuous emotion decay."""
        while self._running:
            try:
                await self.tick()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in emotion tick loop: {e}")
                await asyncio.sleep(interval)
    
    # =========================================================================
    # CORE PROCESSING METHODS
    # =========================================================================
    
    def tick(self):
        """
        Process one tick of emotion simulation.
        Should be called regularly (e.g., every 100-500ms).
        
        This applies decay to all emotions and recalculates complex emotions.
        """
        self.tick_count += 1
        now = time.time()
        delta = now - self.last_tick
        self.last_tick = now
        
        # Decay all basic emotions
        for emotion_state in self.basic_emotions.values():
            emotion_state.decay()
        
        # Recalculate all complex emotions
        for complex_emotion_state in self.complex_emotions.values():
            complex_emotion_state.calculate_intensity(self.basic_emotions)
        
        # Update mood label
        self._update_mood()
        
        # Clean old trigger history
        cutoff = now - 300  # 5 minutes
        self.recent_triggers = [
            (ts, name) for ts, name in self.recent_triggers if ts > cutoff
        ]
        
        # Auto-save periodically
        if self.tick_count % 100 == 0:
            asyncio.create_task(self._save_state())
        
        return self.get_snapshot()
    
    def trigger_emotion(self, emotion: BasicEmotion, intensity: float = 0.5, 
                       source: str = "external"):
        """
        Directly trigger a basic emotion.
        
        Args:
            emotion: The basic emotion to trigger
            intensity: Intensity boost (0.0 - 1.0)
            source: Source of the trigger (for logging)
        """
        if emotion in self.basic_emotions:
            old_intensity = self.basic_emotions[emotion].intensity
            self.basic_emotions[emotion].trigger(intensity)
            
            logger.debug(
                f"Emotion triggered: {emotion.value} ({old_intensity:.2f} -> "
                f"{self.basic_emotions[emotion].intensity:.2f}) [{source}]"
            )
            
            # Record in history
            self.recent_triggers.append((time.time(), f"{source}:{emotion.value}"))
            if len(self.recent_triggers) > self.max_trigger_history:
                self.recent_triggers.pop(0)
    
    def process_text_input(self, text: str, context: dict = None) -> List[Tuple[BasicEmotion, float]]:
        """
        Analyze text input and trigger appropriate emotions.
        
        Args:
            text: The text to analyze
            context: Additional context (speaker, relationship, etc.)
        
        Returns:
            List of (emotion, intensity) tuples that were triggered
        """
        text_lower = text.lower()
        triggered = []
        context = context or {}
        
        # Check each trigger
        for trigger_name, trigger in self.triggers.items():
            if not trigger.can_trigger():
                continue
            
            # Check if any keywords match
            matched = False
            for keyword in trigger.keywords:
                if keyword.lower() in text_lower:
                    matched = True
                    break
            
            if matched:
                # Apply context multipliers
                intensity = trigger.intensity_base
                for ctx_key, multiplier in trigger.context_multipliers.items():
                    if context.get(ctx_key):
                        intensity *= multiplier
                
                # Trigger primary emotion
                primary, base_intensity, secondaries = trigger.trigger()
                self.trigger_emotion(primary, intensity, source=f"trigger:{trigger_name}")
                triggered.append((primary, intensity))
                
                # Trigger secondary emotions
                for secondary_emotion, weight in secondaries.items():
                    secondary_intensity = intensity * weight
                    self.trigger_emotion(secondary_emotion, secondary_intensity, 
                                       source=f"trigger:{trigger_name}")
                    triggered.append((secondary_emotion, secondary_intensity))
                
                logger.debug(f"Text trigger matched: {trigger_name} in '{text[:50]}...'")
        
        return triggered
    
    def process_user_emotion(self, user_emotion: BasicEmotion, intensity: float = 0.5):
        """
        Process detected user emotion and respond with empathy.
        
        This is part of the EQ system - mirroring and responding to user emotions.
        
        Args:
            user_emotion: The emotion detected in the user
            intensity: How strong the user's emotion is
        """
        # Empathetic response
        empathy_factor = self.eq_profile.empathy
        
        if user_emotion == BasicEmotion.JOY:
            # Share joy
            self.trigger_emotion(BasicEmotion.JOY, intensity * empathy_factor, 
                               source="empathy:joy")
            self.trigger_emotion(BasicEmotion.TRUST, intensity * 0.5, 
                               source="empathy:joy")
        
        elif user_emotion == BasicEmotion.SADNESS:
            # Show concern and support
            self.trigger_emotion(BasicEmotion.SADNESS, intensity * empathy_factor * 0.7,
                               source="empathy:sadness")
            self.trigger_emotion(BasicEmotion.TRUST, intensity * empathy_factor * 0.5,
                               source="empathy:sadness")
        
        elif user_emotion == BasicEmotion.ANGER:
            # Stay calm, show concern
            if self.eq_profile.emotion_regulation > 0.6:
                # Regulated response - don't mirror anger
                self.trigger_emotion(BasicEmotion.FEAR, intensity * 0.3,
                                   source="empathy:anger")
                self.trigger_emotion(BasicEmotion.TRUST, 0.2,
                                   source="empathy:anger")
            else:
                # Unregulated - might mirror anger
                self.trigger_emotion(BasicEmotion.ANGER, intensity * 0.4,
                                   source="empathy:anger")
        
        elif user_emotion == BasicEmotion.FEAR:
            # Show support and reassurance
            self.trigger_emotion(BasicEmotion.TRUST, intensity * empathy_factor,
                               source="empathy:fear")
            self.trigger_emotion(BasicEmotion.JOY, intensity * 0.3,
                               source="empathy:fear")
        
        logger.debug(f"Processed user emotion: {user_emotion.value} ({intensity})")
    
    def inject_emotion(self, emotion: BasicEmotion, intensity: float, 
                      reason: str = ""):
        """
        Directly inject an emotion (for debugging or special events).
        
        Args:
            emotion: Emotion to inject
            intensity: Intensity level
            reason: Reason for injection (for logging)
        """
        self.trigger_emotion(emotion, intensity, source=f"inject:{reason}")
        logger.info(f"Emotion injected: {emotion.value} = {intensity} ({reason})")
    
    # =========================================================================
    # STATE QUERY METHODS
    # =========================================================================
    
    def get_emotion_intensity(self, emotion: BasicEmotion) -> float:
        """Get current intensity of a basic emotion."""
        if emotion in self.basic_emotions:
            return self.basic_emotions[emotion].intensity
        return 0.0
    
    def get_complex_emotion_intensity(self, emotion: ComplexEmotion) -> float:
        """Get current intensity of a complex emotion."""
        if emotion in self.complex_emotions:
            return self.complex_emotions[emotion].intensity
        return 0.0
    
    def get_dominant_basic_emotion(self) -> Optional[Tuple[BasicEmotion, float]]:
        """
        Get the most intense basic emotion.
        
        Returns:
            Tuple of (emotion, intensity) or None if all are below threshold
        """
        threshold = self.config.emotion_trigger_threshold
        
        candidates = [
            (emotion, state.intensity)
            for emotion, state in self.basic_emotions.items()
            if state.intensity >= threshold
        ]
        
        if not candidates:
            return None
        
        return max(candidates, key=lambda x: x[1])
    
    def get_dominant_complex_emotion(self) -> Optional[Tuple[ComplexEmotion, float]]:
        """
        Get the most intense complex emotion.
        
        Returns:
            Tuple of (emotion, intensity) or None if all are below threshold
        """
        candidates = [
            (emotion, state.intensity)
            for emotion, state in self.complex_emotions.items()
            if state.is_active()
        ]
        
        if not candidates:
            return None
        
        return max(candidates, key=lambda x: x[1])
    
    def get_all_active_emotions(self) -> Dict[str, float]:
        """Get all emotions (basic + complex) that are currently active."""
        active = {}
        threshold = self.config.emotion_trigger_threshold
        
        # Basic emotions
        for emotion, state in self.basic_emotions.items():
            if state.intensity >= threshold:
                active[f"basic:{emotion.value}"] = state.intensity
        
        # Complex emotions
        for emotion, state in self.complex_emotions.items():
            if state.is_active():
                active[f"complex:{emotion.value}"] = state.intensity
        
        return active
    
    def _update_mood(self):
        """Update the current mood label based on dominant emotions."""
        dominant_basic = self.get_dominant_basic_emotion()
        dominant_complex = self.get_dominant_complex_emotion()
        
        # Complex emotions take precedence
        if dominant_complex and dominant_complex[1] > 0.5:
            self.current_mood = dominant_complex[0].value
        elif dominant_basic:
            self.current_mood = dominant_basic[0].value
        else:
            self.current_mood = "neutral"
        
        # Record in history
        now = time.time()
        if not self.mood_history or self.mood_history[-1][1] != self.current_mood:
            self.mood_history.append((now, self.current_mood))
            # Keep last hour of history
            cutoff = now - 3600
            self.mood_history = [(ts, mood) for ts, mood in self.mood_history if ts > cutoff]
    
    def get_snapshot(self) -> EmotionSnapshot:
        """Get a complete snapshot of current emotion state."""
        basic_dict = {
            e.value: s.intensity for e, s in self.basic_emotions.items()
        }
        complex_dict = {
            e.value: s.intensity for e, s in self.complex_emotions.items()
        }
        
        dominant_basic = self.get_dominant_basic_emotion()
        dominant_complex = self.get_dominant_complex_emotion()
        
        return EmotionSnapshot(
            timestamp=time.time(),
            basic_emotions=basic_dict,
            complex_emotions=complex_dict,
            dominant_basic=dominant_basic[0].value if dominant_basic else None,
            dominant_complex=dominant_complex[0].value if dominant_complex else None,
            mood_label=self.current_mood,
            eq_state=self.eq_profile.to_dict(),
        )
    
    def get_emotion_for_expression(self) -> str:
        """
        Get the emotion code to send to expression system (VTube Studio, etc.).
        
        This applies EQ filtering and returns the most appropriate emotion
        for external expression.
        
        Returns:
            Emotion code string (e.g., "joy", "love", "neutral")
        """
        # Check if we should suppress the dominant emotion
        dominant = self.get_dominant_basic_emotion()
        
        if dominant and self.eq_profile.should_suppress_emotion(dominant[0], dominant[1]):
            # Return a more neutral expression
            return "neutral"
        
        # Check complex emotions first
        complex_dom = self.get_dominant_complex_emotion()
        if complex_dom and complex_dom[1] > 0.4:
            return complex_dom[0].value
        
        # Fall back to basic emotion
        if dominant:
            return dominant[0].value
        
        return "neutral"
    
    # =========================================================================
    # PERSISTENCE METHODS
    # =========================================================================
    
    async def _save_state(self):
        """Save current emotion state to disk."""
        try:
            state_dir = Path("./memory_db")
            state_dir.mkdir(parents=True, exist_ok=True)
            
            state_file = state_dir / "emotion_state.json"
            
            snapshot = self.get_snapshot()
            data = {
                "timestamp": time.time(),
                "basic_emotions": snapshot.basic_emotions,
                "complex_emotions": snapshot.complex_emotions,
                "current_mood": self.current_mood,
                "eq_profile": self.eq_profile.to_dict(),
                "recent_triggers": self.recent_triggers[-20:],  # Last 20
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Emotion state saved")
        except Exception as e:
            logger.error(f"Failed to save emotion state: {e}")
    
    async def _load_state(self):
        """Load emotion state from disk."""
        try:
            state_file = Path("./memory_db/emotion_state.json")
            if not state_file.exists():
                logger.info("No saved emotion state found, starting fresh")
                return
            
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load basic emotions
            for emotion in BasicEmotion:
                if emotion.value in data.get("basic_emotions", {}):
                    intensity = data["basic_emotions"][emotion.value]
                    self.basic_emotions[emotion].intensity = intensity
            
            # Load complex emotions (recalculate from basic)
            for complex_emotion_state in self.complex_emotions.values():
                complex_emotion_state.calculate_intensity(self.basic_emotions)
            
            # Load mood
            self.current_mood = data.get("current_mood", "neutral")
            
            # Load EQ profile
            if "eq_profile" in data:
                eq_data = data["eq_profile"]
                self.eq_profile.self_awareness = eq_data.get("self_awareness", 0.8)
                self.eq_profile.emotion_regulation = eq_data.get("emotion_regulation", 0.7)
                self.eq_profile.empathy = eq_data.get("empathy", 0.75)
                self.eq_profile.social_skill = eq_data.get("social_skill", 0.7)
                self.eq_profile.motivation = eq_data.get("motivation", 0.6)
                self.eq_profile.professionalism_mode = eq_data.get("professionalism_mode", False)
                self.eq_profile.intimacy_level = eq_data.get("intimacy_level", 0.5)
                self.eq_profile.energy_level = eq_data.get("energy_level", 0.7)
            
            # Load recent triggers
            self.recent_triggers = [
                (ts, name) for ts, name in data.get("recent_triggers", [])
            ]
            
            logger.info("Emotion state loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load emotion state: {e}")
    
    # =========================================================================
    # EQ MODIFICATION METHODS
    # =========================================================================
    
    def set_professionalism_mode(self, enabled: bool):
        """Enable/disable professional mode (suppresses negative emotions)."""
        self.eq_profile.professionalism_mode = enabled
        logger.info(f"Professionalism mode: {'enabled' if enabled else 'disabled'}")
    
    def adjust_intimacy(self, delta: float):
        """Adjust intimacy level with user."""
        self.eq_profile.intimacy_level = max(0.0, min(1.0, 
            self.eq_profile.intimacy_level + delta))
        logger.debug(f"Intimacy adjusted to: {self.eq_profile.intimacy_level:.2f}")
    
    def adjust_energy(self, delta: float):
        """Adjust overall emotional energy level."""
        self.eq_profile.energy_level = max(0.0, min(1.0,
            self.eq_profile.energy_level + delta))
        logger.debug(f"Energy adjusted to: {self.eq_profile.energy_level:.2f}")
    
    def train_empathy(self, user_feedback: str):
        """
        Adjust empathy based on user feedback.
        
        Args:
            user_feedback: "positive" or "negative"
        """
        if user_feedback == "positive":
            self.eq_profile.empathy = min(1.0, self.eq_profile.empathy + 0.02)
        elif user_feedback == "negative":
            self.eq_profile.empathy = max(0.0, self.eq_profile.empathy - 0.02)
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def reset_all_emotions(self):
        """Reset all emotions to baseline (neutral state)."""
        for state in self.basic_emotions.values():
            state.intensity = 0.0
            state.trigger_count = 0
        
        for state in self.complex_emotions.values():
            state.intensity = 0.0
        
        self.current_mood = "neutral"
        logger.info("All emotions reset to neutral")
    
    def get_statistics(self) -> dict:
        """Get statistics about emotion engine usage."""
        total_triggers = sum(s.trigger_count for s in self.basic_emotions.values())
        
        return {
            "tick_count": self.tick_count,
            "total_triggers": total_triggers,
            "current_mood": self.current_mood,
            "active_emotions_count": len(self.get_all_active_emotions()),
            "recent_trigger_count": len(self.recent_triggers),
            "eq_profile_summary": {
                "empathy": self.eq_profile.empathy,
                "regulation": self.eq_profile.emotion_regulation,
                "energy": self.eq_profile.energy_level,
            }
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        snapshot = self.get_snapshot()
        return (
            f"EmotionEngine(mood={snapshot.mood_label}, "
            f"dominant={snapshot.dominant_basic or 'none'}, "
            f"active={len(self.get_all_active_emotions())} emotions)"
        )


# =============================================================================
# EMOTION EXPRESSION MAPPER
# =============================================================================

class EmotionExpressionMapper:
    """
    Maps emotion states to expression codes for VTube Studio or other avatar systems.
    
    This provides a bridge between the internal emotion representation and
    external expression systems.
    """
    
    # Default mapping of emotion codes to VTube Studio hotkey IDs
    DEFAULT_VTS_MAPPING = {
        "neutral": "Idle",
        "joy": "Happy",
        "sadness": "Sad",
        "anger": "Angry",
        "fear": "Scared",
        "surprise": "Surprised",
        "disgust": "Disgusted",
        "trust": "Relaxed",
        "anticipation": "Excited",
        
        # Complex emotions
        "love": "Love",
        "optimism": "Hopeful",
        "remorse": "Guilty",
        "awe": "Amazed",
        "contempt": "Smug",
        "aggressiveness": "Determined",
        "excitement": "VeryHappy",
        "confusion": "Confused",
        "boredom": "Bored",
        "curiosity": "Curious",
        "empathy": "Concerned",
        "frustration": "Frustrated",
        "contentment": "Content",
    }
    
    def __init__(self, custom_mapping: dict = None):
        """
        Initialize the mapper.
        
        Args:
            custom_mapping: Custom emotion -> expression mapping
        """
        self.mapping = self.DEFAULT_VTS_MAPPING.copy()
        if custom_mapping:
            self.mapping.update(custom_mapping)
        
        # Expression priority (higher = more important to show)
        self.priority = {
            "neutral": 0,
            "boredom": 1,
            "contentment": 2,
            "trust": 3,
            "anticipation": 4,
            "curiosity": 5,
            "joy": 6,
            "surprise": 7,
            "fear": 8,
            "sadness": 9,
            "disgust": 10,
            "anger": 11,
            "frustration": 12,
            "aggressiveness": 13,
            "love": 14,
            "excitement": 15,
        }
    
    def map_emotion_to_expression(self, emotion_code: str) -> str:
        """
        Map an emotion code to an expression/hotkey ID.
        
        Args:
            emotion_code: The emotion code from EmotionEngine
        
        Returns:
            Expression/hotkey ID for VTube Studio
        """
        return self.mapping.get(emotion_code, self.mapping["neutral"])
    
    def get_best_expression(self, active_emotions: Dict[str, float]) -> str:
        """
        Select the best expression given multiple active emotions.
        
        Args:
            active_emotions: Dict of emotion_code -> intensity
        
        Returns:
            Best expression/hotkey ID
        """
        if not active_emotions:
            return self.mapping["neutral"]
        
        # Score each emotion: intensity * priority
        scored = []
        for emotion, intensity in active_emotions.items():
            priority = self.priority.get(emotion, 5)
            score = intensity * priority
            scored.append((emotion, score))
        
        if not scored:
            return self.mapping["neutral"]
        
        # Pick highest scored emotion
        best_emotion = max(scored, key=lambda x: x[1])[0]
        return self.map_emotion_to_expression(best_emotion)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "BasicEmotion",
    "ComplexEmotion",
    "EQTrait",
    
    # Data classes
    "BasicEmotionState",
    "ComplexEmotionState",
    "EQProfile",
    "EmotionTrigger",
    "EmotionSnapshot",
    
    # Main classes
    "EmotionEngine",
    "EmotionExpressionMapper",
    
    # Constants
    "DEFAULT_TRIGGERS",
    "DEFAULT_COMPLEX_EMOTIONS",
]
