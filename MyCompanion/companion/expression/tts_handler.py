"""
TTS Handler - Text-to-Speech with Anime Voices
Uses Edge TTS for high-quality, free, multi-voice synthesis
Supports Japanese anime-style voices and emotional inflection
"""
import asyncio
import logging
import edge_tts
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class TTSHandler:
    """
    Async Text-to-Speech using Edge TTS
    
    Features:
    - Free, no API key required
    - Multiple anime-style Japanese voices
    - Emotional pitch/rate adjustment
    - Streaming audio output
    - Queue management for overlapping speech
    """
    
    # Anime-style voices (Japanese & English)
    VOICES = {
        # Japanese female voices (anime style)
        'miku_jp': 'ja-JP-NanamiNeural',           # Warm, friendly
        'hatsune_miku': 'ja-JP-KeitaNeural',       # Energetic
        'yuki': 'ja-JP-AoiNeural',                 # Young, cute
        'sakura': 'ja-JP-MayuNeural',              # Soft, gentle
        'rei': 'ja-JP-DaichiNeural',               # Cool, mature
        
        # English voices (for bilingual support)
        'miku_en': 'en-US-AnaNeural',              # Friendly American
        'british': 'en-GB-SoniaNeural',            # British female
        'australian': 'en-AU-NatashaNeural',       # Australian
        
        # Special/emotional voices
        'whisper': 'en-US-AnaNeural',              # Quiet (rate adjusted)
        'excited': 'ja-JP-NanamiNeural',           # Fast, high pitch
        'sad': 'en-US-AnaNeural',                  # Slow, low pitch
    }
    
    # Voice characteristics for emotional modulation
    VOICE_PROFILES = {
        'neutral': {'rate': '+0%', 'pitch': '+0Hz', 'volume': '+0%'},
        'happy': {'rate': '+10%', 'pitch': '+5Hz', 'volume': '+5%'},
        'excited': {'rate': '+20%', 'pitch': '+10Hz', 'volume': '+10%'},
        'sad': {'rate': '-15%', 'pitch': '-5Hz', 'volume': '-5%'},
        'angry': {'rate': '+15%', 'pitch': '-3Hz', 'volume': '+15%'},
        'concerned': {'rate': '-5%', 'pitch': '-2Hz', 'volume': '-3%'},
        'playful': {'rate': '+12%', 'pitch': '+8Hz', 'volume': '+5%'},
        'thoughtful': {'rate': '-10%', 'pitch': '+0Hz', 'volume': '-5%'},
        'curious': {'rate': '+5%', 'pitch': '+6Hz', 'volume': '+0%'},
        'whisper': {'rate': '-20%', 'pitch': '-8Hz', 'volume': '-30%'},
    }
    
    def __init__(self, default_voice: str = 'miku_jp'):
        self.default_voice = default_voice
        self.current_voice = default_voice
        self.is_speaking = False
        self.speech_queue: asyncio.Queue = asyncio.Queue()
        self.current_task: Optional[asyncio.Task] = None
        self.output_device = None  # Can set specific audio device
        
        # Statistics
        self.total_speeches = 0
        self.total_characters = 0
        self.start_time = datetime.now()
        
        logger.info(f"TTS initialized with default voice: {default_voice}")
    
    async def speak(
        self,
        text: str,
        emotion: str = 'neutral',
        voice: Optional[str] = None,
        priority: bool = False
    ):
        """
        Add text to speech queue
        
        Args:
            text: Text to speak
            emotion: Emotion code for voice modulation
            voice: Override default voice
            priority: If True, interrupt current speech
        """
        if priority:
            # Clear queue and interrupt
            self.speech_queue = asyncio.Queue()
            if self.current_task and not self.current_task.done():
                self.current_task.cancel()
                await asyncio.sleep(0.1)  # Brief pause
        
        # Add to queue
        await self.speech_queue.put({
            'text': text,
            'emotion': emotion,
            'voice': voice or self.current_voice,
            'timestamp': datetime.now()
        })
        
        # Start speaker if not running
        if not self.is_speaking:
            self.current_task = asyncio.create_task(self._process_queue())
    
    async def _process_queue(self):
        """Process speech queue continuously"""
        self.is_speaking = True
        
        try:
            while True:
                try:
                    # Get next item with timeout
                    item = await asyncio.wait_for(
                        self.speech_queue.get(),
                        timeout=0.5
                    )
                    
                    await self._generate_and_play(
                        text=item['text'],
                        emotion=item['emotion'],
                        voice=item['voice']
                    )
                    
                except asyncio.TimeoutError:
                    # Queue empty
                    break
                except asyncio.CancelledError:
                    logger.debug("Speech task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Queue processing error: {e}")
                    continue
                    
        finally:
            self.is_speaking = False
    
    async def _generate_and_play(
        self,
        text: str,
        emotion: str,
        voice: str
    ):
        """Generate TTS audio and play it"""
        try:
            # Get voice profile
            profile = self.VOICE_PROFILES.get(emotion, self.VOICE_PROFILES['neutral'])
            
            # Select actual voice
            voice_name = self.VOICES.get(voice, self.VOICES[self.default_voice])
            
            # Create communicate object with SSML for emotion
            ssml = self._create_ssml(text, profile)
            
            communicate = edge_tts.Communicate(
                text=ssml,
                voice=voice_name,
                rate=profile['rate'],
                pitch=profile['pitch'],
                volume=profile['volume']
            )
            
            # Generate audio stream
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # Could use for lip sync timing
                    pass
            
            if not audio_chunks:
                logger.warning("No audio generated")
                return
            
            # Combine chunks
            audio_data = b''.join(audio_chunks)
            
            # Play audio
            await self._play_audio(audio_data)
            
            # Update stats
            self.total_speeches += 1
            self.total_characters += len(text)
            
            logger.debug(f"Spoke {len(text)} chars with emotion={emotion}, voice={voice}")
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
    
    def _create_ssml(self, text: str, profile: Dict[str, str]) -> str:
        """
        Create SSML markup for enhanced speech
        
        SSML (Speech Synthesis Markup Language) allows fine control
        """
        # Basic SSML with prosody control
        ssml = f"""<?xml version="1.0"?>
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <prosody rate="{profile['rate']}" pitch="{profile['pitch']}" volume="{profile['volume']}">
        {self._escape_xml(text)}
    </prosody>
</speak>"""
        return ssml
    
    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))
    
    async def _play_audio(self, audio_data: bytes):
        """
        Play audio data through system speakers
        
        Uses pygame for simple playback on all platforms
        """
        try:
            import pygame
            import io
            
            # Initialize pygame mixer if needed
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
            
            # Load audio from bytes
            audio_file = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for completion
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
        except ImportError:
            # Fallback: save to file and use system player
            await self._play_audio_fallback(audio_data)
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            await self._play_audio_fallback(audio_data)
    
    async def _play_audio_fallback(self, audio_data: bytes):
        """Fallback audio playback using system commands"""
        try:
            # Save to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            # Play using system command
            import platform
            import subprocess
            
            system = platform.system()
            if system == 'Windows':
                subprocess.run(['powershell', '-c', f'(New-Object Media.SoundPlayer "{temp_path}").PlaySync()'], 
                             capture_output=True)
            elif system == 'Darwin':  # macOS
                subprocess.run(['afplay', temp_path], capture_output=True)
            else:  # Linux
                subprocess.run(['aplay', temp_path], capture_output=True)
            
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"Fallback playback failed: {e}")
    
    async def stop(self):
        """Stop current speech immediately"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
        
        # Clear queue
        self.speech_queue = asyncio.Queue()
        self.is_speaking = False
        
        try:
            import pygame
            pygame.mixer.music.stop()
        except:
            pass
        
        logger.debug("Speech stopped")
    
    def set_voice(self, voice_name: str):
        """Change current voice"""
        if voice_name in self.VOICES:
            self.current_voice = voice_name
            logger.info(f"Voice changed to: {voice_name}")
        else:
            logger.warning(f"Unknown voice: {voice_name}")
    
    def list_voices(self) -> List[str]:
        """List available voice names"""
        return list(self.VOICES.keys())
    
    def get_stats(self) -> Dict:
        """Get TTS statistics"""
        uptime = (datetime.now() - self.start_time).total_seconds() / 60
        return {
            'total_speeches': self.total_speeches,
            'total_characters': self.total_characters,
            'avg_chars_per_speech': self.total_characters / self.total_speeches if self.total_speeches > 0 else 0,
            'is_speaking': self.is_speaking,
            'queue_size': self.speech_queue.qsize(),
            'current_voice': self.current_voice,
            'uptime_minutes': uptime,
            'speeches_per_minute': self.total_speeches / uptime if uptime > 0 else 0
        }
    
    async def test_voice(self, voice_name: Optional[str] = None):
        """Test a voice with sample text"""
        test_texts = {
            'miku_jp': 'こんにちは！私はミクです。よろしくね！',
            'miku_en': 'Hello! I\'m Miku, your AI companion!',
            'excited': 'This is so exciting! Let\'s have fun!',
            'sad': 'Sometimes things don\'t go as planned...',
            'playful': 'Hehe, want to play a game?',
        }
        
        voice = voice_name or self.default_voice
        text = test_texts.get(voice, 'Testing voice output quality.')
        
        logger.info(f"Testing voice: {voice}")
        await self.speak(text, emotion='neutral', voice=voice, priority=True)


# Convenience function for quick TTS
async def quick_speak(text: str, emotion: str = 'neutral'):
    """Quick one-line TTS usage"""
    tts = TTSHandler()
    await tts.speak(text, emotion=emotion, priority=True)
    await asyncio.sleep(0.5)  # Brief wait for playback start
