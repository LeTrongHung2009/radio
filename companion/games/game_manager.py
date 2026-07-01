"""
Game Agent Manager
==================

Manages multiple game agents and provides unified interface.
"""

import asyncio
import logging
from typing import Optional, Type
from datetime import datetime

from ..config import get_config
from .game_state import GameState, GameEvent, GameEventType
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class GameAgentManager:
    """Manages game-specific AI agents."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.config = get_config()
        self.event_bus = event_bus or EventBus.get_instance()
        
        self.agents: dict[str, object] = {}
        self.active_game: Optional[str] = None
        self.game_states: dict[str, GameState] = {}
        
        self._running = False
        
    def register_agent(self, game_id: str, agent: object):
        """Register a game agent."""
        self.agents[game_id] = agent
        logger.info(f"Registered agent for game: {game_id}")
        
    async def start_game(self, game_id: str) -> bool:
        """Start a game agent."""
        if game_id not in self.agents:
            logger.error(f"No agent registered for game: {game_id}")
            return False
            
        if self.active_game:
            logger.warning(f"Already playing {self.active_game}, stopping first")
            await self.stop_game(self.active_game)
            
        agent = self.agents[game_id]
        
        try:
            # Initialize game state
            state = GameState(
                game_id=game_id,
                game_name=game_id,
                is_active=True,
                session_start=datetime.utcnow(),
            )
            self.game_states[game_id] = state
            
            # Start the agent
            if hasattr(agent, 'start'):
                if asyncio.iscoroutinefunction(agent.start):
                    await agent.start()
                else:
                    agent.start()
                    
            self.active_game = game_id
            logger.info(f"Started game: {game_id}")
            
            # Publish event
            await self.event_bus.publish('game_started', {
                'game_id': game_id,
                'state': state.to_dict(),
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting game {game_id}: {e}", exc_info=True)
            return False
            
    async def stop_game(self, game_id: str):
        """Stop a game agent."""
        if game_id not in self.agents:
            return
            
        agent = self.agents[game_id]
        
        try:
            # Stop the agent
            if hasattr(agent, 'stop'):
                if asyncio.iscoroutinefunction(agent.stop):
                    await agent.stop()
                else:
                    agent.stop()
                    
            # Update state
            if game_id in self.game_states:
                self.game_states[game_id].is_active = False
                
            if self.active_game == game_id:
                self.active_game = None
                
            logger.info(f"Stopped game: {game_id}")
            
            # Publish event
            await self.event_bus.publish('game_ended', {'game_id': game_id})
            
        except Exception as e:
            logger.error(f"Error stopping game {game_id}: {e}", exc_info=True)
            
    async def pause_game(self, game_id: str):
        """Pause a game."""
        if game_id not in self.game_states:
            return
            
        self.game_states[game_id].is_paused = True
        
        agent = self.agents.get(game_id)
        if agent and hasattr(agent, 'pause'):
            if asyncio.iscoroutinefunction(agent.pause):
                await agent.pause()
            else:
                agent.pause()
                
        await self.event_bus.publish('game_paused', {'game_id': game_id})
        
    async def resume_game(self, game_id: str):
        """Resume a paused game."""
        if game_id not in self.game_states:
            return
            
        self.game_states[game_id].is_paused = False
        
        agent = self.agents.get(game_id)
        if agent and hasattr(agent, 'resume'):
            if asyncio.iscoroutinefunction(agent.resume):
                await agent.resume()
            else:
                agent.resume()
                
        await self.event_bus.publish('game_resumed', {'game_id': game_id})
        
    def get_game_state(self, game_id: str) -> Optional[GameState]:
        """Get the current state of a game."""
        return self.game_states.get(game_id)
        
    def get_active_game(self) -> Optional[str]:
        """Get the currently active game."""
        return self.active_game
        
    def is_game_active(self, game_id: str) -> bool:
        """Check if a game is currently active."""
        state = self.game_states.get(game_id)
        return state is not None and state.is_active and not state.is_paused
        
    async def execute_action(self, game_id: str, action: str, params: dict = None):
        """Execute an action in a game."""
        if game_id not in self.agents:
            logger.error(f"No agent for game: {game_id}")
            return False
            
        agent = self.agents[game_id]
        
        if not hasattr(agent, 'execute_action'):
            logger.error(f"Agent for {game_id} doesn't support execute_action")
            return False
            
        try:
            result = await agent.execute_action(action, params or {})
            
            # Update last action
            if game_id in self.game_states:
                from .game_state import GameAction
                try:
                    self.game_states[game_id].last_action = GameAction[action.upper()]
                except KeyError:
                    pass
                self.game_states[game_id].last_action_time = datetime.utcnow()
                
            return result
            
        except Exception as e:
            logger.error(f"Error executing action {action} in {game_id}: {e}")
            return False
            
    async def get_screenshot(self, game_id: str) -> Optional[bytes]:
        """Get a screenshot of the game."""
        if game_id not in self.agents:
            return None
            
        agent = self.agents[game_id]
        
        if hasattr(agent, 'get_screenshot'):
            try:
                return await agent.get_screenshot()
            except Exception as e:
                logger.error(f"Error getting screenshot: {e}")
                
        return None
        
    def get_all_registered_games(self) -> list[str]:
        """Get list of all registered game IDs."""
        return list(self.agents.keys())
        
    @property
    def total_games(self) -> int:
        """Get total number of registered games."""
        return len(self.agents)


# Singleton instance
_game_manager: Optional[GameAgentManager] = None


def get_game_agent_manager() -> GameAgentManager:
    """Get or create the singleton game agent manager."""
    global _game_manager
    if _game_manager is None:
        _game_manager = GameAgentManager()
    return _game_manager
