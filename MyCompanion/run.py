#!/usr/bin/env python3
"""
Miku - AI Desktop Companion
Main entry point integrating PyQt6 GUI with async backend via qasync

Usage:
    python run.py
    
Requirements:
    - .env file with GROQ_API_KEY
    - PyQt6, qasync installed
    - Optional: VTube Studio for avatar display
"""
import sys
import os
import asyncio
import signal
import logging
from pathlib import Path

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('miku.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Setup environment and paths"""
    # Add project root to path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Load .env file
    env_file = project_root / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    else:
        logger.warning(f"No .env file found at {env_file}")
    
    # Create necessary directories
    dirs = [
        project_root / 'memory_db',
        project_root / 'persona/private',
        project_root / 'logs',
        project_root / 'temp'
    ]
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Environment setup complete")


async def main_async():
    """Main async entry point"""
    logger.info("=" * 60)
    logger.info("🌸 Starting Miku - AI Desktop Companion")
    logger.info("=" * 60)
    
    try:
        # Import after environment setup
        from companion.config import Config
        from companion.bot import initialize_orchestrator
        from qasync import QAsyncApplication
        
        # Load configuration
        config = Config()
        
        # Validate required config
        if not config.GROQ_API_KEY:
            logger.error("""
❗ CRITICAL: No GROQ_API_KEY found!

To get your FREE Groq API key:
1. Visit: https://console.groq.com/keys
2. Sign up for free account
3. Create a new API key
4. Add to .env file: GROQ_API_KEY=your_key_here

Miku will start in limited demo mode without API key.
""")
        
        # Create Qt application with async integration
        app = QAsyncApplication(sys.argv)
        app.setApplicationName("Miku")
        app.setOrganizationName("MyCompanion")
        
        # Initialize orchestrator
        orchestrator = initialize_orchestrator(config)
        await orchestrator.setup()
        
        # Show chat widget
        if orchestrator.chat_widget:
            orchestrator.chat_widget.show()
            logger.info("Chat widget displayed (top-right corner)")
        
        # Handle shutdown signals
        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(orchestrator.shutdown())
            app.quit()
        
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        # Start background tasks
        run_task = asyncio.create_task(orchestrator.run())
        
        logger.info("""
╔═══════════════════════════════════════════════════════╗
║          🌸 Miku is now running!                      ║
╠═══════════════════════════════════════════════════════╣
║ • Chat widget: Top-right corner of screen            ║
║ • Type messages and press Enter to chat              ║
║ • Double-click tray icon to show/hide                ║
║ • Press Ctrl+C to quit                               ║
╚═══════════════════════════════════════════════════════╝
""")
        
        # Run event loop (integrates Qt and asyncio)
        await run_task
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Miku shutdown complete")


def main():
    """Main entry point"""
    try:
        # Setup environment
        setup_environment()
        
        # Run async main
        asyncio.run(main_async())
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
