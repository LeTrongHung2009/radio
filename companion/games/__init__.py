"""
Games Module - Game Agent Management
=====================================

Manages game-specific AI agents for autonomous gameplay.
Supports multiple games with different agent implementations.
"""

from .game_manager import GameAgentManager, get_game_agent_manager
from .pokemon_agent import PokemonFireRedAgent
from .chess_agent import ChessAgent
from .game_state import GameState, GameAction, GameEventType

__all__ = [
    'GameAgentManager',
    'get_game_agent_manager',
    'PokemonFireRedAgent',
    'ChessAgent',
    'GameState',
    'GameAction',
    'GameEventType',
]
