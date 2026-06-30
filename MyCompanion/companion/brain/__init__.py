"""
MyCompanion Framework - Brain Module Initialization

This package contains all AI inference and cognitive processing modules.
All operations are async to avoid blocking the GUI event loop.
"""

from .ai_core import AICore
from .groq_client import GroqClient
from .companion_state import CompanionState

__all__ = [
    "AICore",
    "GroqClient", 
    "CompanionState",
]
