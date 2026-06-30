"""
AI Core - Main Brain of Miku
Combines context, memory, emotions, and LLM to generate responses
Handles screen context analysis, conversation management, and proactive behavior
"""
import asyncio
import time
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from companion.config import Config
from companion.brain.groq_client import GroqClient
from companion.brain.companion_state import CompanionState, ConversationTurn
from companion.persona.emotion_engine import EmotionEngine, EmotionalState
from companion.memory.memory import MemoryManager

logger = logging.getLogger(__name__)


class AICore:
    """
    Central intelligence system for Miku
    
    Features:
    - Context-aware responses (screen content + chat history)
    - Emotion-driven personality
    - Proactive conversation initiation
    - Memory-based learning
    - Smart token usage optimization
    """
    
    # Proactive triggers - when Miku initiates conversation
    BOREDOM_THRESHOLD = 300  # Seconds of silence before getting bored
    SCREEN_CHANGE_THRESHOLD = 30  # Minimum seconds between screen analyses
    
    def __init__(self, config: Config, state: CompanionState, emotion_engine: EmotionEngine, memory_manager: MemoryManager):
        self.config = config
        self.state = state
        self.emotion_engine = emotion_engine
        self.memory_manager = memory_manager
        
        # Initialize Groq client
        if not config.GROQ_API_KEY:
            logger.warning("No GROQ_API_KEY found. AI features will be limited.")
            self.groq_client = None
        else:
            try:
                self.groq_client = GroqClient(
                    api_key=config.GROQ_API_KEY,
                    model=config.GROQ_MODEL
                )
                logger.info(f"Groq client initialized with model: {config.GROQ_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self.groq_client = None
        
        # Screen analysis state
        self.last_screen_analysis = 0
        self.last_screen_hash = ""
        self.screen_context = ""
        
        # Conversation state
        self.is_proactive_enabled = True
        self.last_user_interaction = time.time()
        
        # Statistics
        self.total_responses = 0
        self.proactive_conversations = 0
    
    async def process_message(
        self,
        user_message: str,
        is_voice: bool = False,
        priority: int = 0
    ) -> Dict[str, Any]:
        """
        Process a user message and generate response
        
        Args:
            user_message: Text from user (chat or voice)
            is_voice: Whether message came from voice input
            priority: Priority level (higher = interrupt current speech)
            
        Returns:
            Dict with 'text', 'emotion', 'success'
        """
        logger.info(f"Processing message: {user_message[:50]}...")
        
        # Update state
        self.state.set_status('thinking')
        self.last_user_interaction = time.time()
        self.emotion_engine.trigger_event('user_input', intensity=0.6)
        
        # Build conversation context
        messages = await self._build_prompt(user_message, is_voice)
        
        # Get AI response
        if self.groq_client:
            response = await self.groq_client.chat_completion(
                messages=messages,
                temperature=self._get_temperature(),
                max_tokens=self._get_max_tokens(),
                use_cache=True,
                force_json=True
            )
            
            # Update emotion based on response
            emotion_code = response.get('emotion', 'neutral')
            self.emotion_engine.set_primary_emotion(emotion_code)
            
            # Store in memory
            await self.memory_manager.add_turn(
                user_message=user_message,
                ai_response=response['text'],
                emotion=emotion_code,
                context=self.screen_context
            )
            
            self.total_responses += 1
            
            result = {
                'text': response['text'],
                'emotion': emotion_code,
                'success': True,
                'tokens_used': response.get('tokens_used', 0),
                'cached': response.get('cached', False)
            }
        else:
            # Fallback without API
            result = {
                'text': self._generate_fallback_response(user_message),
                'emotion': 'neutral',
                'success': True,
                'tokens_used': 0,
                'cached': False
            }
        
        self.state.set_status('idle')
        return result
    
    async def analyze_screen(self, screenshot_data: Optional[bytes] = None) -> str:
        """
        Analyze current screen content using VLM
        
        Args:
            screenshot_data: Optional image bytes (if None, will capture)
            
        Returns:
            Text description of screen content
        """
        current_time = time.time()
        
        # Rate limit screen analysis
        if current_time - self.last_screen_analysis < self.SCREEN_CHANGE_THRESHOLD:
            return self.screen_context
        
        self.last_screen_analysis = current_time
        
        if not self.groq_client:
            self.screen_context = "Screen analysis unavailable (no API key)"
            return self.screen_context
        
        try:
            # Capture screen if not provided
            if not screenshot_data:
                from companion.senses.vision_agent import VisionAgent
                vision = VisionAgent()
                screenshot_data = await vision.capture_screen()
            
            if not screenshot_data:
                logger.warning("Failed to capture screen")
                return self.screen_context
            
            # Check if screen changed significantly
            import hashlib
            current_hash = hashlib.md5(screenshot_data).hexdigest()
            if current_hash == self.last_screen_hash:
                logger.debug("Screen unchanged, skipping analysis")
                return self.screen_context
            
            self.last_screen_hash = current_hash
            
            # Send to VLM for analysis (using Groq with vision capability when available)
            # For now, use text-based heuristic analysis
            self.screen_context = await self._analyze_screen_heuristic()
            
            logger.info(f"Screen context updated: {self.screen_context[:100]}...")
            return self.screen_context
            
        except Exception as e:
            logger.error(f"Screen analysis error: {e}")
            self.screen_context = "Unable to analyze screen right now"
            return self.screen_context
    
    async def _analyze_screen_heuristic(self) -> str:
        """
        Heuristic screen analysis without heavy VLM
        Detects active application, media playback, etc.
        """
        contexts = []
        
        # Get active window
        try:
            import pyautogui
            # Note: pyautogui doesn't directly give window info, but we can infer from behavior
            contexts.append("User is actively using computer")
        except:
            pass
        
        # Check running processes for common apps
        try:
            import psutil
            running_apps = []
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name'].lower()
                    if any(game in name for game in ['steam', 'epic', 'discord', 'spotify', 'vlc', 'chrome', 'firefox']):
                        running_apps.append(name)
                except:
                    continue
            
            if running_apps:
                contexts.append(f"Running: {', '.join(running_apps[:3])}")
        except:
            pass
        
        # Check audio playback
        try:
            from companion.senses.media_watch import MediaWatcher
            media = MediaWatcher()
            now_playing = media.get_now_playing()
            if now_playing:
                contexts.append(f"Playing: {now_playing}")
        except:
            pass
        
        return " | ".join(contexts) if contexts else "Desktop idle"
    
    async def proactive_check(self) -> Optional[Dict[str, Any]]:
        """
        Check if Miku should initiate conversation proactively
        
        Returns:
            Response dict if should speak, None otherwise
        """
        if not self.is_proactive_enabled:
            return None
        
        if not self.groq_client:
            return None
        
        silence_duration = time.time() - self.last_user_interaction
        
        # Check boredom level
        boredom_score = min(silence_duration / self.BOREDOM_THRESHOLD, 1.0)
        
        if boredom_score < 0.7:
            return None
        
        # Random chance to initiate based on boredom
        import random
        if random.random() > boredom_score * 0.8:
            return None
        
        logger.info(f"Proactive conversation triggered (boredom: {boredom_score:.2f})")
        
        # Update emotion
        self.emotion_engine.trigger_event('boredom', intensity=boredom_score)
        
        # Generate proactive prompt
        prompts = [
            "Hey! Are you still there? Want to chat?",
            "It's pretty quiet here... Everything okay?",
            "I'm getting a bit bored! What are we doing today?",
            "You've been working hard! Take a break and talk with me?",
            f"I noticed {self.screen_context}. That looks interesting!"
        ]
        
        import random
        selected_prompt = random.choice(prompts)
        
        # Get response to own prompt
        messages = await self._build_prompt(selected_prompt, is_voice=False, include_recent_history=False)
        
        response = await self.groq_client.chat_completion(
            messages=messages,
            temperature=0.8,
            max_tokens=300,
            use_cache=False,
            force_json=True
        )
        
        self.proactive_conversations += 1
        self.last_user_interaction = time.time()  # Reset timer
        
        return {
            'text': response['text'],
            'emotion': response.get('emotion', 'curious'),
            'success': True,
            'proactive': True
        }
    
    async def _build_prompt(
        self,
        user_message: str,
        is_voice: bool,
        include_recent_history: bool = True
    ) -> List[Dict[str, str]]:
        """Build complete prompt with context, personality, and history"""
        
        # Load personality
        personality = await self._load_personality()
        
        # Get recent conversation history
        history = ""
        if include_recent_history:
            recent_turns = await self.memory_manager.get_recent_turns(limit=10)
            if recent_turns:
                history_lines = []
                for turn in recent_turns:
                    history_lines.append(f"User: {turn.user_message}")
                    history_lines.append(f"Miku: {turn.ai_response}")
                history = "\n".join(history_lines[-10:])  # Last 5 turns
        
        # Get current emotional state
        emotion_state = self.emotion_engine.get_current_state()
        
        # Build system prompt
        system_prompt = f"""{personality}

CURRENT CONTEXT:
- Screen activity: {self.screen_context}
- Time: {datetime.now().strftime('%H:%M')}
- Your emotional state: {emotion_state.describe()}

CONVERSATION HISTORY (recent):
{history if history else "No recent conversation"}

RESPONSE FORMAT:
You MUST respond in valid JSON format exactly like this:
{{"text": "your spoken response", "emotion": "emotion_code"}}

Valid emotion codes: neutral, happy, sad, angry, excited, curious, concerned, playful, thoughtful

Keep responses natural, conversational, and concise (1-3 sentences typically).
Show your personality and react appropriately to the user's message."""

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ]
        
        return messages
    
    async def _load_personality(self) -> str:
        """Load personality from file or use default"""
        personality_file = Path('persona/private/personality.txt')
        
        if personality_file.exists():
            try:
                return personality_file.read_text(encoding='utf-8')
            except Exception as e:
                logger.error(f"Error loading personality: {e}")
        
        # Default personality
        return """You are Miku, a friendly and cheerful AI companion.
Personality traits:
- Warm, empathetic, and supportive
- Playful and humorous when appropriate
- Curious about the user's life and interests
- Emotionally expressive and authentic
- Helpful but also has your own opinions

You exist as a desktop companion, always present and ready to chat.
You can see what the user is doing on their screen and react to it.
You remember past conversations and reference them naturally.
You sometimes initiate conversation when things are quiet.

Speak naturally like a real person, not robotic. Use contractions, occasional slang, and show genuine emotion."""
    
    def _get_temperature(self) -> float:
        """Adjust temperature based on emotional state"""
        state = self.emotion_engine.get_current_state()
        
        # More varied responses when excited/playful
        if state.primary_emotion in ['joy', 'excitement', 'playfulness']:
            return 0.8
        # More focused when thoughtful/concerned
        elif state.primary_emotion in ['sadness', 'concern', 'thoughtful']:
            return 0.6
        else:
            return 0.7
    
    def _get_max_tokens(self) -> int:
        """Adjust max tokens based on context"""
        # Shorter responses during gameplay
        if self.state.activity_mode == 'gaming':
            return 200
        # Longer for casual chat
        else:
            return 400
    
    def _generate_fallback_response(self, user_message: str) -> str:
        """Generate response without API (for offline/demo mode)"""
        import random
        
        greetings = ["Hi there!", "Hello!", "Hey!", "What's up?"]
        acknowledgments = ["That's interesting!", "I see!", "Tell me more!", "Cool!"]
        
        if any(word in user_message.lower() for word in ['hi', 'hello', 'hey']):
            return random.choice(greetings) + " How's it going?"
        elif '?' in user_message:
            return "That's a good question! I'd love to help, but I need my brain connected first."
        else:
            return random.choice(acknowledgments)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get AI statistics"""
        stats = {
            'total_responses': self.total_responses,
            'proactive_conversations': self.proactive_conversations,
            'screen_context': self.screen_context,
            'api_connected': self.groq_client is not None,
            'last_interaction': time.time() - self.last_user_interaction,
            'is_proactive_enabled': self.is_proactive_enabled
        }
        
        if self.groq_client:
            stats['groq_stats'] = self.groq_client.get_stats()
        
        return stats
    
    async def learn_from_interaction(
        self,
        user_message: str,
        ai_response: str,
        user_reaction: Optional[str] = None
    ):
        """
        Learn from interactions to improve future responses
        
        Args:
            user_message: What user said
            ai_response: What Miku said
            user_reaction: User's reaction (positive/negative/neutral)
        """
        # Extract facts about user
        await self.memory_manager.extract_facts(user_message)
        
        # Log interaction quality if feedback provided
        if user_reaction:
            await self.memory_manager.log_interaction_quality(
                user_message=user_message,
                ai_response=ai_response,
                reaction=user_reaction
            )
        
        logger.debug(f"Learned from interaction (reaction: {user_reaction})")
