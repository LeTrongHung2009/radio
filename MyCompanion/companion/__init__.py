"""
Miku AI Companion - Desktop AI Assistant
A comprehensive AI companion inspired by Neuro-Sama and Kira.
Optimized for low-spec hardware with AMD GPU support.
"""

__version__ = "1.0.0"
__author__ = "Miku Developer"
__description__ = "Desktop AI Companion with emotions, memory, and desktop interaction"

from .config import get_config as config, Config

__all__ = [
    "config",
    "Config",
]
