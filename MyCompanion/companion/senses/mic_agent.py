"""
Microphone Agent - Voice input handling
Uses Groq Whisper API for fast, accurate speech-to-text
"""
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class MicAgent:
    """
    Microphone input and speech recognition
    
    Features:
    - Continuous listening mode
    - Wake word detection (optional)
    - Groq Whisper API integration
    - Voice activity detection
    """
    
    def __init__(self):
        self.is_listening = False
        self.callback: Optional[Callable] = None
        self.wake_word_enabled = False
        self.audio_queue = asyncio.Queue()
        
        logger.info("Mic agent initialized")
    
    async def start_listening(
        self,
        callback: Callable[[str], None],
        wake_word_enabled: bool = False
    ):
        """
        Start continuous listening
        
        Args:
            callback: Function to call with transcribed text
            wake_word_enabled: Whether to require wake word
        """
        self.callback = callback
        self.wake_word_enabled = wake_word_enabled
        self.is_listening = True
        
        logger.info(f"Listening started (wake word: {'ON' if wake_word_enabled else 'OFF'})")
        
        # Start audio capture loop
        await self._audio_loop()
    
    async def _audio_loop(self):
        """Main audio processing loop"""
        try:
            import sounddevice as sd
            import numpy as np
            
            # Audio parameters
            sample_rate = 16000
            chunk_size = 8000  # 0.5 seconds
            
            # Simple voice activity detection
            silence_threshold = 0.01
            silence_duration = 2.0  # seconds
            silence_counter = 0
            
            def audio_callback(indata, frames, time, status):
                """Process incoming audio"""
                if status:
                    logger.warning(f"Audio status: {status}")
                
                # Calculate RMS energy
                rms = np.sqrt(np.mean(indata ** 2))
                
                # Check for voice activity
                if rms > silence_threshold:
                    silence_counter = 0
                    asyncio.create_task(self.audio_queue.put(indata.copy()))
                else:
                    silence_counter += frames / sample_rate
                    
                    # If silence detected and we have audio, process it
                    if silence_counter >= silence_duration:
                        silence_counter = 0
            
            # Start audio stream
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                callback=audio_callback,
                blocksize=chunk_size
            ):
                logger.info("Audio stream started")
                
                while self.is_listening:
                    # Process audio chunks
                    try:
                        audio_chunk = await asyncio.wait_for(
                            self.audio_queue.get(),
                            timeout=1.0
                        )
                        
                        # Transcribe when enough audio collected
                        # For now, just log (full implementation would batch and transcribe)
                        
                    except asyncio.TimeoutError:
                        continue
                        
        except ImportError:
            logger.warning("sounddevice not available, using fallback")
            await self._fallback_listening()
        except Exception as e:
            logger.error(f"Audio loop error: {e}", exc_info=True)
            if self.is_listening:
                logger.info("Restarting audio loop after error...")
                await asyncio.sleep(5)
                await self._audio_loop()
    
    async def _fallback_listening(self):
        """Fallback without sounddevice"""
        logger.info("Running in fallback mode (no real mic input)")
        
        while self.is_listening:
            await asyncio.sleep(10)
            
            # Simulate occasional test message
            if self.callback:
                # Don't actually send anything in fallback
                pass
    
    async def stop(self):
        """Stop listening"""
        self.is_listening = False
        logger.info("Listening stopped")
    
    async def transcribe_audio(self, audio_data) -> Optional[str]:
        """
        Transcribe audio using Groq Whisper API
        
        Args:
            audio_data: Audio bytes
            
        Returns:
            Transcribed text or None
        """
        try:
            from groq import AsyncGroq
            import os
            
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                logger.error("No GROQ_API_KEY for transcription")
                return None
            
            client = AsyncGroq(api_key=api_key)
            
            # Save audio to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            
            # Transcribe
            with open(temp_path, 'rb') as f:
                transcription = await client.audio.transcriptions.create(
                    file=(temp_path, f.read()),
                    model="whisper-large-v3",
                    language="en"
                )
            
            # Cleanup
            import os
            os.unlink(temp_path)
            
            text = transcription.text.strip()
            logger.debug(f"Transcribed: {text}")
            return text
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None


# Convenience function
async def quick_listen() -> Optional[str]:
    """Quick one-time listen"""
    agent = MicAgent()
    # Would need full implementation for actual use
    return None
