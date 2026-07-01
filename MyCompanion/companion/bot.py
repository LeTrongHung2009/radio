"""
Bot Orchestrator - Main coordination system for Miku
Manages all subsystems, event loops, turn-taking, and proactive behavior
Integrates GUI (PyQt6) with async operations via qasync
"""
import asyncio
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from companion.config import Config
from companion.brain.companion_state import CompanionState
from companion.brain.ai_core import AICore
from companion.persona.emotion_engine import EmotionEngine
from companion.memory.memory import MemoryManager
from companion.expression.tts_handler import TTSHandler
from companion.desktop.chat_widget import ChatWidget
from companion.senses.vision_agent import VisionAgent
from companion.senses.mic_agent import MicAgent

logger = logging.getLogger(__name__)


class BotOrchestrator:
    """
    Central coordinator for all Miku subsystems
    
    Responsibilities:
    - Initialize and manage all components
    - Coordinate async event loop with Qt GUI
    - Handle user input (chat, voice)
    - Manage turn-taking and speech priority
    - Run proactive behavior loop
    - Monitor system health
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.start_time = datetime.now()
        
        # Core state
        self.state = CompanionState()
        self.emotion_engine = EmotionEngine()
        
        # Subsystems (initialized in setup)
        self.memory_manager: Optional[MemoryManager] = None
        self.ai_core: Optional[AICore] = None
        self.tts_handler: Optional[TTSHandler] = None
        self.vision_agent: Optional[VisionAgent] = None
        self.mic_agent: Optional[MicAgent] = None
        self.chat_widget: Optional[ChatWidget] = None
        
        # Task management
        self.proactive_task: Optional[asyncio.Task] = None
        self.screen_analysis_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Statistics
        self.messages_processed = 0
        self.voice_interactions = 0
        self.proactive_triggers = 0
        
        logger.info("Bot orchestrator initialized")
    
    async def setup(self):
        """Initialize all subsystems"""
        logger.info("Setting up Miku subsystems...")
        
        try:
            # Memory system
            self.memory_manager = MemoryManager(config=self.config)
            await self.memory_manager.initialize()
            logger.info("✓ Memory system ready")
            
            # AI Core
            self.ai_core = AICore(
                config=self.config,
                state=self.state,
                emotion_engine=self.emotion_engine,
                memory_manager=self.memory_manager
            )
            logger.info("✓ AI Core ready")
            
            # TTS Handler
            self.tts_handler = TTSHandler(
                default_voice=self.config.TTS_VOICE
            )
            logger.info("✓ TTS ready")
            
            # Vision Agent (optional)
            if self.config.ENABLE_VISION:
                self.vision_agent = VisionAgent()
                logger.info("✓ Vision agent ready")
            
            # Microphone Agent (optional)
            if self.config.ENABLE_VOICE_INPUT:
                self.mic_agent = MicAgent()
                logger.info("✓ Mic agent ready")
            
            # Desktop Widget
            self.chat_widget = ChatWidget()
            self.chat_widget.message_sent.connect(self._on_chat_message)
            logger.info("✓ Desktop widget ready")
            
            logger.info("=" * 50)
            logger.info("🌸 Miku System Fully Initialized!")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise
    
    def _on_chat_message(self, text: str):
        """Handle chat widget message (called from Qt thread)"""
        # Schedule async processing
        asyncio.create_task(self.process_user_message(text, is_voice=False))
    
    async def process_user_message(
        self,
        text: str,
        is_voice: bool = False,
        priority: int = 0
    ):
        """
        Process user message through full pipeline
        
        Args:
            text: User's message
            is_voice: Whether from voice input
            priority: Priority level for interrupting
        """
        logger.info(f"Processing {'voice' if is_voice else 'chat'} message: {text[:50]}...")
        
        if is_voice:
            self.voice_interactions += 1
        
        # Update state
        self.state.set_status('listening')
        self.messages_processed += 1
        
        try:
            # Get AI response
            response = await self.ai_core.process_message(
                user_message=text,
                is_voice=is_voice,
                priority=priority
            )
            
            if response['success']:
                # Speak response
                await self.tts_handler.speak(
                    text=response['text'],
                    emotion=response['emotion'],
                    priority=(priority > 0)
                )
                
                # Update widget
                if self.chat_widget and not is_voice:
                    self.chat_widget.add_response(response['text'])
                    self.chat_widget.set_typing_indicator(False)
                
                # Update emotion display (for VTube Studio if connected)
                await self._update_expression(response['emotion'])
                
                logger.info(f"Response: {response['text'][:100]}...")
            else:
                error_detail = response.get('error', 'unknown')
                logger.warning(f"AI response failed: {error_detail}")
                
                # Still deliver the fallback text to the user
                if response.get('text'):
                    await self.tts_handler.speak(
                        text=response['text'],
                        emotion=response.get('emotion', 'neutral'),
                        priority=False
                    )
                    if self.chat_widget and not is_voice:
                        self.chat_widget.add_response(response['text'])
                        self.chat_widget.set_typing_indicator(False)
                
        except Exception as e:
            logger.error(f"Message processing error: {e}", exc_info=True)
            if self.chat_widget:
                self.chat_widget.set_typing_indicator(False)
        finally:
            self.state.set_status('idle')
    
    async def _update_expression(self, emotion: str):
        """Update avatar expression based on emotion"""
        # Placeholder for VTube Studio integration
        # Would call vts_client to trigger hotkey/expression
        logger.debug(f"Expression updated: {emotion}")
    
    async def start_proactive_loop(self):
        """Run background task for proactive conversation"""
        logger.info("Starting proactive behavior loop...")
        
        while self.running:
            try:
                # Check if should initiate conversation
                if not self.state.is_speaking and not self.state.is_listening:
                    response = await self.ai_core.proactive_check()
                    
                    if response:
                        self.proactive_triggers += 1
                        logger.info(f"Proactive conversation #{self.proactive_triggers}")
                        
                        await self.tts_handler.speak(
                            text=response['text'],
                            emotion=response['emotion'],
                            priority=False
                        )
                
                # Sleep between checks
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proactive loop error: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def start_screen_analysis_loop(self):
        """Periodically analyze screen content"""
        if not self.config.ENABLE_VISION:
            return
        
        logger.info("Starting screen analysis loop...")
        
        while self.running:
            try:
                if not self.state.is_speaking:  # Don't analyze while talking
                    await self.ai_core.analyze_screen()
                
                # Analyze every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Screen analysis error: {e}")
                await asyncio.sleep(60)
    
    async def start_voice_listener(self):
        """Start continuous voice listening (wake word detection)"""
        if not self.config.ENABLE_VOICE_INPUT or not self.mic_agent:
            return
        
        logger.info("Starting voice listener...")
        
        try:
            await self.mic_agent.start_listening(
                callback=self._on_voice_detected,
                wake_word_enabled=self.config.USE_WAKE_WORD
            )
        except Exception as e:
            logger.error(f"Voice listener failed: {e}")
    
    def _on_voice_detected(self, text: str):
        """Handle detected voice transcription"""
        logger.info(f"Voice detected: {text}")
        asyncio.create_task(self.process_user_message(text, is_voice=True, priority=1))
    
    async def run(self):
        """Main run loop - starts all background tasks"""
        self.running = True
        
        logger.info("Starting Miku...")
        
        # Start background tasks
        self.proactive_task = asyncio.create_task(self.start_proactive_loop())
        
        if self.config.ENABLE_VISION:
            self.screen_analysis_task = asyncio.create_task(self.start_screen_analysis_loop())
        
        if self.config.ENABLE_VOICE_INPUT:
            asyncio.create_task(self.start_voice_listener())
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
            
            # Periodic health check
            if int(time.time()) % 60 == 0:
                await self._health_check()
    
    async def _health_check(self):
        """Periodic system health monitoring"""
        try:
            stats = self.get_stats()
            
            # Log key metrics
            logger.info(
                f"Health check: {stats['messages_processed']} msgs, "
                f"{stats['uptime_minutes']:.1f}min uptime, "
                f"API: {stats['api_status']}"
            )
            
            # Check for issues
            groq_stats = stats.get('groq_stats')
            if groq_stats and groq_stats.get('current_rpm', 0) >= 28:
                logger.warning("Approaching API rate limit!")
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Miku...")
        self.running = False
        
        # Cancel background tasks
        for task in [self.proactive_task, self.screen_analysis_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop TTS
        if self.tts_handler:
            await self.tts_handler.stop()
        
        # Stop mic
        if self.mic_agent:
            await self.mic_agent.stop()
        
        # Save memory
        if self.memory_manager:
            await self.memory_manager.save()
        
        logger.info("Miku shut down complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        uptime = (datetime.now() - self.start_time).total_seconds() / 60
        
        stats = {
            'messages_processed': self.messages_processed,
            'voice_interactions': self.voice_interactions,
            'proactive_triggers': self.proactive_triggers,
            'uptime_minutes': uptime,
            'is_running': self.running,
            'current_status': self.state.status,
            'api_status': 'connected' if self.ai_core and self.ai_core.groq_client else 'disconnected',
            'emotion': self.emotion_engine.get_current_state().primary_emotion
        }
        
        # Add subsystem stats
        if self.ai_core:
            stats['ai_stats'] = self.ai_core.get_stats()
        
        if self.tts_handler:
            stats['tts_stats'] = self.tts_handler.get_stats()
        
        if self.memory_manager:
            stats['memory_stats'] = self.memory_manager.get_stats()
        
        if self.ai_core and self.ai_core.groq_client:
            stats['groq_stats'] = self.ai_core.groq_client.get_stats()
        
        return stats
    
    def toggle_mute(self):
        """Toggle TTS mute"""
        if self.tts_handler:
            # Implement mute logic
            logger.info("TTS muted/unmuted")
    
    def toggle_proactive(self):
        """Toggle proactive behavior"""
        if self.ai_core:
            self.ai_core.is_proactive_enabled = not self.ai_core.is_proactive_enabled
            logger.info(f"Proactive behavior: {'ON' if self.ai_core.is_proactive_enabled else 'OFF'}")


# Singleton instance
_orchestrator: Optional[BotOrchestrator] = None


def get_orchestrator() -> BotOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized!")
    return _orchestrator


def initialize_orchestrator(config: Config) -> BotOrchestrator:
    """Initialize global orchestrator"""
    global _orchestrator
    _orchestrator = BotOrchestrator(config)
    return _orchestrator
