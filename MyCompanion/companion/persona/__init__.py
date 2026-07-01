"""Persona Module - Personality and emotion management for AI Companion"""

from companion.persona.emotion_engine import EmotionEngine, EmotionSnapshot
from companion.persona.internal_monologue import InternalMonologueEngine
from companion.persona.personality_loader import (
    PersonalityLoader,
    PersonalityConfig,
    get_personality_loader,
    initialize_personality_loader
)

__all__ = [
    'EmotionEngine',
    'EmotionSnapshot',
    'InternalMonologueEngine',
    'PersonalityLoader',
    'PersonalityConfig',
    'get_personality_loader',
    'initialize_personality_loader'
]
