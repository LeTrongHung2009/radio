#!/usr/bin/env python3
"""
Miku AI Companion - Main Entry Point
Launches the desktop AI assistant with PyQt6 and asyncio integration.
Optimized for Arch Linux with AMD GPU support.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Miku.Launcher")

def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    
    try:
        import qasync
    except ImportError:
        missing.append("qasync")
    
    try:
        import aiohttp
    except ImportError:
        missing.append("aiohttp")
    
    try:
        import dotenv
    except ImportError:
        missing.append("python-dotenv")
    
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.error("Run: pip install -r requirements.txt")
        return False
    
    logger.info("All dependencies checked successfully")
    return True

def check_env():
    """Check if .env file exists and has required keys"""
    env_path = project_root / ".env"
    if not env_path.exists():
        logger.warning(".env file not found. Copy .env.example to .env and configure.")
        return False
    
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key or groq_key == "gsk_your_groq_api_key_here":
        logger.warning("GROQ_API_KEY not configured in .env")
        logger.warning("Get a free key at: https://console.groq.com/keys")
    
    return True

async def main_async():
    """Main async entry point"""
    logger.info("=" * 60)
    logger.info("Miku AI Companion v1.0.0")
    logger.info("=" * 60)
    
    # Import config
    from companion.config import config
    logger.info("Configuration loaded")
    
    # Check API availability
    preferred_provider = config.get_preferred_provider()
    logger.info(f"Using AI provider: {preferred_provider.upper()}")
    
    # Import and create bot
    from companion.bot import MikuBot
    
    logger.info("Initializing MikuBot...")
    bot = MikuBot()
    
    # Initialize all systems
    logger.info("Loading personality...")
    await bot.initialize_persona()
    
    logger.info("Initializing memory system...")
    await bot.initialize_memory()
    
    logger.info("Initializing TTS engine...")
    await bot.initialize_tts()
    
    logger.info("Initializing vision system...")
    await bot.initialize_vision()
    
    logger.info("Initializing desktop widget...")
    await bot.initialize_desktop()
    
    logger.info("Starting dashboard server...")
    await bot.start_dashboard()
    
    # Start the main bot loop
    logger.info("=" * 60)
    logger.info("🌸 MIKU AI COMPANION READY 🌸")
    logger.info("=" * 60)
    logger.info("Use the chat widget to talk to Miku")
    logger.info("Press Ctrl+C to exit")
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
    finally:
        logger.info("Cleaning up...")
        await bot.shutdown()
        logger.info("Goodbye!")

def main():
    """Main entry point with qasync integration"""
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    check_env()
    
    # Try to import qasync for Qt-asyncio integration
    try:
        from qasync import QAsyncApplication, async_run
        from PyQt6.QtWidgets import QApplication
        
        # Create Qt application
        app = QAsyncApplication(sys.argv)
        app.setApplicationName("Miku AI Companion")
        app.setOrganizationName("MikuProject")
        
        # Run async main
        async_run(main_async())
        
    except ImportError as e:
        logger.warning(f"qasync not available, using pure asyncio: {e}")
        logger.warning("Desktop widget features may be limited")
        
        # Fallback to pure asyncio
        try:
            asyncio.run(main_async())
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
