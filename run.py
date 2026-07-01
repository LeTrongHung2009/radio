"""
KIRA - Multimodal Memory-Persistent AI VTuber Framework
========================================================

A real-time cognitive agent with long-term semantic memory, computer vision,
full voice interaction, mood-driven Live2D expressions, on-screen synced captions,
live chess on Lichess, and proactive autonomous behavior.

This is the main entry point for launching Kira.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from companion.bot import KiraBot
from companion.config import get_config
from companion.dashboard import get_web_configurator
from companion.identity import get_identity_manager
from companion.persona import get_personality_loader
from companion.brain import get_turn_arbiter, initialize_turn_arbiter
from companion.expression import get_avatar_renderer, initialize_avatar_renderer
from companion.memory import get_semantic_db
from companion.streaming import get_chat_platform_manager
from companion.games import get_game_agent_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT_DIR / 'kira.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for Kira."""
    logger.info("=" * 80)
    logger.info("KIRA - Multimodal AI VTuber Framework")
    logger.info("=" * 80)
    
    # Load configuration
    config = get_config()
    logger.info(f"Configuration loaded: {config.PROJECT_NAME} v{config.VERSION}")
    
    # Initialize core components
    logger.info("Initializing identity manager...")
    identity_mgr = get_identity_manager()
    
    logger.info("Loading personality...")
    persona_loader = get_personality_loader()
    if not persona_loader.current_profile:
        persona_loader.create_miku_default()
    
    logger.info("Initializing turn arbiter...")
    turn_arbiter = initialize_turn_arbiter()
    
    logger.info("Initializing avatar renderer...")
    avatar_renderer = initialize_avatar_renderer()
    
    logger.info("Connecting to semantic memory...")
    memory_db = get_semantic_db()
    
    # Initialize streaming platforms
    logger.info("Initializing chat platform manager...")
    chat_manager = get_chat_platform_manager()
    
    # Initialize game agents
    logger.info("Initializing game agent manager...")
    game_manager = get_game_agent_manager()
    
    # Create and configure bot
    logger.info("Creating Kira bot instance...")
    bot = KiraBot(
        config=config,
        identity_manager=identity_mgr,
        personality_loader=persona_loader,
        turn_arbiter=turn_arbiter,
        avatar_renderer=avatar_renderer,
        memory_db=memory_db,
        chat_manager=chat_manager,
        game_manager=game_manager
    )
    
    # Setup web dashboard
    logger.info("Setting up web dashboard...")
    dashboard = get_web_configurator()
    dashboard.set_components(
        identity_manager=identity_mgr,
        personality_loader=persona_loader,
        turn_arbiter=turn_arbiter,
        avatar_renderer=avatar_renderer,
        memory_db=memory_db,
        bot=bot
    )
    
    # Start all systems
    logger.info("Starting all systems...")
    try:
        # Start dashboard in background
        dashboard_task = asyncio.create_task(dashboard.start())
        
        # Start main bot loop
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Shutdown signal received...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Cleaning up resources...")
        await bot.shutdown()
        await dashboard.stop()
        logger.info("Kira shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
