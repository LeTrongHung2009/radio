"""
3-Layer Emotional State Matrix

Layer 1 - Reflexive Reaction  (instantaneous, decays fast)
Layer 2 - Ambient Mood        (slow drift over minutes)
Layer 3 - Core Personality    (immutable traits)

The combined state drives prompt generation and VTS expressions.
"""

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

VALID_EMOTIONS = (
    "neutral",
    "happy",
    "sad",
    "angry",
    "excited",
    "curious",
    "concerned",
    "playful",
    "thoughtful",
    "surprised",
    "bored",
    "smug",
    "embarrassed",
)


class CoreTrait(Enum):
    SASSY = "sassy"
    SHARP_WITTED = "sharp_witted"
    CURIOUS = "curious"
    CUTE = "cute"
    ATTACHED = "attached"


@dataclass
class EmotionSnapshot:
    """Immutable snapshot of the full emotional state at a point in time."""

    reflex_emotion: str
    reflex_intensity: float
    mood_emotion: str
    mood_intensity: float
    core_traits: list[str]
    valence: float  # -1.0 (negative) to +1.0 (positive)
    arousal: float  # 0.0 (calm) to 1.0 (excited)
    dominant_emotion: str

    def describe(self) -> str:
        parts = [
            f"Feeling: {self.dominant_emotion}",
            f"(reflex={self.reflex_emotion}@{self.reflex_intensity:.1f}",
            f"mood={self.mood_emotion}@{self.mood_intensity:.1f}",
            f"valence={self.valence:+.2f} arousal={self.arousal:.2f})",
        ]
        return " ".join(parts)


@dataclass
class _ReflexLayer:
    """Layer 1: instantaneous reflex, decays within seconds."""

    emotion: str = "neutral"
    intensity: float = 0.0
    triggered_at: float = field(default_factory=time.monotonic)
    decay_rate: float = 0.15  # intensity units per second

    def tick(self) -> None:
        elapsed = time.monotonic() - self.triggered_at
        self.intensity = max(0.0, self.intensity - elapsed * self.decay_rate)
        if self.intensity <= 0.01:
            self.emotion = "neutral"
            self.intensity = 0.0
        self.triggered_at = time.monotonic()

    def fire(self, emotion: str, intensity: float = 0.8) -> None:
        self.emotion = emotion
        self.intensity = min(1.0, intensity)
        self.triggered_at = time.monotonic()


@dataclass
class _MoodLayer:
    """Layer 2: slow ambient mood, drifts over minutes."""

    emotion: str = "neutral"
    intensity: float = 0.3
    _history: list[tuple[str, float]] = field(default_factory=list)
    drift_rate: float = 0.02  # per event

    def nudge(self, emotion: str, delta: float = 0.1) -> None:
        self._history.append((emotion, delta))
        if len(self._history) > 30:
            self._history = self._history[-30:]
        self._recalculate()

    def _recalculate(self) -> None:
        if not self._history:
            return
        scores: dict[str, float] = {}
        for emo, d in self._history:
            scores[emo] = scores.get(emo, 0.0) + d
        best = max(scores, key=lambda k: scores[k])
        self.emotion = best
        self.intensity = min(1.0, scores[best] / max(1, len(self._history)) * 3)

    def decay(self) -> None:
        self.intensity = max(0.0, self.intensity - 0.005)
        if self.intensity <= 0.01:
            self.emotion = "neutral"


class EmotionMatrix:
    """
    Full 3-layer emotion system.

    Layer 3 (core traits) is immutable and always present.
    """

    CORE_TRAITS = [
        CoreTrait.SASSY,
        CoreTrait.SHARP_WITTED,
        CoreTrait.CURIOUS,
        CoreTrait.CUTE,
        CoreTrait.ATTACHED,
    ]

    _REFLEX_MAP: dict[str, tuple[str, float]] = {
        "user_input": ("happy", 0.5),
        "compliment": ("happy", 0.9),
        "insult": ("angry", 0.7),
        "game_over": ("surprised", 0.8),
        "code_error": ("concerned", 0.6),
        "screen_change": ("curious", 0.4),
        "boredom": ("bored", 0.6),
        "greeting": ("excited", 0.7),
        "farewell": ("sad", 0.5),
    }

    _VALENCE_MAP: dict[str, float] = {
        "happy": 0.8,
        "excited": 0.9,
        "playful": 0.6,
        "curious": 0.3,
        "neutral": 0.0,
        "thoughtful": 0.1,
        "bored": -0.2,
        "concerned": -0.3,
        "sad": -0.6,
        "angry": -0.7,
        "surprised": 0.2,
        "smug": 0.4,
        "embarrassed": -0.1,
    }

    _AROUSAL_MAP: dict[str, float] = {
        "excited": 0.9,
        "angry": 0.8,
        "surprised": 0.7,
        "happy": 0.6,
        "playful": 0.6,
        "curious": 0.5,
        "smug": 0.4,
        "embarrassed": 0.4,
        "concerned": 0.4,
        "thoughtful": 0.3,
        "neutral": 0.2,
        "sad": 0.3,
        "bored": 0.1,
    }

    def __init__(self) -> None:
        self._reflex = _ReflexLayer()
        self._mood = _MoodLayer()

    def trigger_reflex(self, event: str) -> Optional[str]:
        mapping = self._REFLEX_MAP.get(event)
        if mapping is None:
            return None
        emotion, intensity = mapping
        self._reflex.fire(emotion, intensity)
        self._mood.nudge(emotion, 0.1)
        logger.debug("Reflex: %s -> %s@%.1f", event, emotion, intensity)
        return emotion

    def apply_response_emotion(self, emotion: str) -> None:
        if emotion in VALID_EMOTIONS:
            self._mood.nudge(emotion, 0.15)

    def snapshot(self) -> EmotionSnapshot:
        self._reflex.tick()
        self._mood.decay()

        dominant = self._reflex.emotion if self._reflex.intensity > 0.3 else self._mood.emotion

        valence = self._VALENCE_MAP.get(dominant, 0.0)
        arousal = self._AROUSAL_MAP.get(dominant, 0.2)

        return EmotionSnapshot(
            reflex_emotion=self._reflex.emotion,
            reflex_intensity=self._reflex.intensity,
            mood_emotion=self._mood.emotion,
            mood_intensity=self._mood.intensity,
            core_traits=[t.value for t in self.CORE_TRAITS],
            valence=valence,
            arousal=arousal,
            dominant_emotion=dominant,
        )

    @property
    def temperature(self) -> float:
        snap = self.snapshot()
        if snap.arousal > 0.6:
            return 0.85
        if snap.arousal < 0.3:
            return 0.6
        return 0.7
