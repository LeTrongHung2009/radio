"""
MyCompanion Framework - Configuration Module

This module loads all configuration from environment variables and provides
a centralized Config class for accessing settings throughout the application.

Designed for AMD GPU / CPU-only operation with cloud-based AI inference.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """
    Centralized configuration for MyCompanion Framework.
    
    All values are loaded from environment variables (.env file).
    Defaults are provided for safe operation.
    """
    
    # =========================================================================
    # CLOUD API KEYS
    # =========================================================================
    
    groq_api_key: str = Field(default="", description="Groq API key for fast LLM inference")
    openai_api_key: str = Field(default="", description="OpenAI API key for GPT-4o Vision / Whisper")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude models")
    hf_token: str = Field(default="", description="HuggingFace token for gated models")
    
    # =========================================================================
    # LLM CONFIGURATION
    # =========================================================================
    
    # Primary LLM endpoint (Groq recommended for speed and free tier)
    llm_provider: str = Field(default="groq", description="Primary LLM provider: groq, openai, anthropic")
    llm_model: str = Field(default="llama-3.1-8b-instant", description="Model ID for primary LLM")
    
    # Vision model endpoint
    vision_provider: str = Field(default="openai", description="Vision model provider")
    vision_model: str = Field(default="gpt-4o-mini", description="Vision model ID")
    
    # STT endpoint
    stt_provider: str = Field(default="openai", description="STT provider: openai (Whisper)")
    stt_model: str = Field(default="whisper-1", description="STT model ID")
    
    # API timeouts and retries
    api_timeout_seconds: int = Field(default=30, description="Timeout for API requests")
    api_max_retries: int = Field(default=3, description="Maximum retry attempts for failed API calls")
    api_retry_delay_base: float = Field(default=1.0, description="Base delay for exponential backoff")
    
    # =========================================================================
    # TTS CONFIGURATION (Edge TTS - Free, High Quality)
    # =========================================================================
    
    tts_voice: str = Field(default="ja-JP-NanamiNeural", description="Edge TTS voice ID")
    tts_rate: str = Field(default="+20%", description="TTS speech rate")
    tts_volume: str = Field(default="+10%", description="TTS volume level")
    tts_output_dir: str = Field(default="./voices", description="Directory for TTS audio output")
    
    # Anime-style voice presets
    ANIME_VOICES: dict = {
        "nanami": "ja-JP-NanamiNeural",      # Warm, friendly female
        "aoi": "ja-JP-AoiNeural",            # Young, energetic female
        "misaki": "ja-JP-MisakiNeural",      # Mature female
        "ana": "en-US-AnaNeural",            # American female
        "aria": "en-GB-AriaNeural",          # British female
    }
    
    # =========================================================================
    # TWITCH INTEGRATION (Optional)
    # =========================================================================
    
    twitch_app_id: str = Field(default="", description="Twitch app ID")
    twitch_app_secret: str = Field(default="", description="Twitch app secret")
    twitch_redirect_uri: str = Field(default="http://localhost:17563", description="Twitch OAuth redirect URI")
    twitch_channel: str = Field(default="", description="Twitch channel name to monitor")
    twitch_enabled: bool = Field(default=False, description="Enable Twitch chat integration")
    
    # =========================================================================
    # VTube Studio Configuration (Optional)
    # =========================================================================
    
    vts_host: str = Field(default="127.0.0.1", description="VTube Studio WebSocket host")
    vts_port: int = Field(default=8001, description="VTube Studio WebSocket port")
    vts_auth_token: str = Field(default="", description="VTube Studio auth token")
    vts_enabled: bool = Field(default=False, description="Enable VTube Studio integration")
    
    # =========================================================================
    # AUDIO DEVICE SETTINGS
    # =========================================================================
    
    mic_device_number: int = Field(default=1, description="Microphone device number")
    speaker_device_number: int = Field(default=2, description="Speaker device number")
    
    # =========================================================================
    # DASHBOARD & SERVER SETTINGS
    # =========================================================================
    
    dashboard_port: int = Field(default=8080, description="Web dashboard server port")
    socketio_cors_origins: List[str] = Field(
        default=["http://localhost:8080", "http://127.0.0.1:8080"],
        description="Allowed CORS origins for Socket.IO (avoid ['*'] in production)"
    )
    
    # =========================================================================
    # VISION SETTINGS
    # =========================================================================
    
    screenshot_interval: float = Field(default=30.0, description="Interval between automatic screenshots (seconds)")
    screenshot_quality: int = Field(default=85, description="JPEG quality for screenshots (1-100)")
    screenshot_max_width: int = Field(default=640, description="Max width for screenshot resizing")
    vision_enabled: bool = Field(default=False, description="Enable automatic screen vision")
    
    # Salience filter settings
    salience_threshold: float = Field(default=0.3, description="Threshold for detecting screen changes")
    salience_cooldown: float = Field(default=10.0, description="Cooldown before re-analyzing similar screens")
    
    # =========================================================================
    # MEMORY SETTINGS
    # =========================================================================
    
    memory_db_path: str = Field(default="./memory_db/local_facts.json", description="Path to local facts database")
    identity_path: str = Field(default="./memory_db/identity.json", description="Path to identity file")
    log_path: str = Field(default="./logs", description="Directory for session logs")
    
    # Memory limits
    max_short_term_memories: int = Field(default=50, description="Maximum short-term memories to retain")
    max_long_term_memories: int = Field(default=500, description="Maximum long-term memories to retain")
    memory_decay_hours: float = Field(default=24.0, description="Hours before memories start decaying")
    
    # =========================================================================
    # PERSONALITY SETTINGS
    # =========================================================================
    
    personality_path: str = Field(default="./persona/private/personality.txt", description="Path to personality file")
    
    # =========================================================================
    # EMOTION ENGINE SETTINGS
    # =========================================================================
    
    emotion_decay_rate: float = Field(default=0.95, description="Rate at which emotions decay per tick (0-1)")
    emotion_trigger_threshold: float = Field(default=0.3, description="Threshold to trigger emotional response")
    eq_management_enabled: bool = Field(default=True, description="Enable emotional intelligence management")
    
    # =========================================================================
    # GAME MODE & ACTIVITY DETECTION
    # =========================================================================
    
    game_mode_enabled: bool = Field(default=True, description="Enable game mode detection")
    focus_apps: List[str] = Field(default=["game", "video", "music", "work", "browser"], 
                                   description="Categories of applications to detect")
    
    # Response length limits based on activity
    max_response_tokens_game: int = Field(default=30, description="Max tokens when user is gaming")
    max_response_tokens_idle: int = Field(default=100, description="Max tokens when user is idle")
    max_response_tokens_work: int = Field(default=50, description="Max tokens when user is working")
    
    # =========================================================================
    # INTERACTION SETTINGS
    # =========================================================================
    
    wake_word_enabled: bool = Field(default=True, description="Enable wake word detection")
    wake_words: List[str] = Field(default=["miku", "hey miku", "ok miku"], 
                                   description="Words that trigger AI attention")
    
    auto_respond_delay_min: float = Field(default=0.5, description="Minimum delay before auto-response (seconds)")
    auto_respond_delay_max: float = Field(default=2.0, description="Maximum delay before auto-response (seconds)")
    
    boredom_threshold_seconds: float = Field(default=60.0, description="Seconds of silence before boredom triggers")
    boredom_prompt_enabled: bool = Field(default=True, description="Enable boredom-initiated conversation")
    
    # =========================================================================
    # DESKTOP WIDGET SETTINGS
    # =========================================================================
    
    widget_always_on_top: bool = Field(default=True, description="Keep chat widget always on top")
    widget_opacity: float = Field(default=0.9, description="Widget window opacity (0.0-1.0)")
    widget_width: int = Field(default=400, description="Chat widget width in pixels")
    widget_height: int = Field(default=600, description="Chat widget height in pixels")
    widget_theme: str = Field(default="dark", description="Widget theme: dark, light, anime")
    
    # =========================================================================
    # SYSTEM SETTINGS
    # =========================================================================
    
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")
    debug_mode: bool = Field(default=False, description="Enable debug mode with verbose logging")
    
    # Resource management
    max_cpu_usage_percent: int = Field(default=70, description="Maximum CPU usage percentage target")
    low_resource_mode: bool = Field(default=False, description="Enable low resource mode for weak hardware")
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        dirs = [
            self.tts_output_dir,
            os.path.dirname(self.memory_db_path),
            os.path.dirname(self.identity_path),
            self.log_path,
            os.path.dirname(self.personality_path),
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    @property
    def is_groq_available(self) -> bool:
        """Check if Groq API is configured."""
        return bool(self.groq_api_key)
    
    @property
    def is_openai_available(self) -> bool:
        """Check if OpenAI API is configured."""
        return bool(self.openai_api_key)
    
    @property
    def is_anthropic_available(self) -> bool:
        """Check if Anthropic API is configured."""
        return bool(self.anthropic_api_key)
    
    @property
    def is_twitch_enabled(self) -> bool:
        """Check if Twitch integration is fully configured."""
        return self.twitch_enabled and bool(self.twitch_app_id) and bool(self.twitch_app_secret)
    
    @property
    def is_vts_enabled(self) -> bool:
        """Check if VTube Studio is configured."""
        return self.vts_enabled and bool(self.vts_auth_token)
    
    @property
    def is_vision_enabled(self) -> bool:
        """Check if vision capabilities are available."""
        return self.vision_enabled and self.is_openai_available
    
    def get_llm_endpoint_url(self) -> str:
        """Get the appropriate LLM endpoint URL based on provider."""
        endpoints = {
            "groq": "https://api.groq.com/openai/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
        }
        return endpoints.get(self.llm_provider, endpoints["groq"])
    
    def get_api_key(self) -> str:
        """Get the API key for the current primary LLM provider."""
        keys = {
            "groq": self.groq_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
        }
        return keys.get(self.llm_provider, self.groq_api_key)
    
    def set_anime_voice(self, voice_name: str):
        """Set TTS voice to a preset anime voice."""
        if voice_name in self.ANIME_VOICES:
            self.tts_voice = self.ANIME_VOICES[voice_name]
            logger.info(f"Set anime voice to: {voice_name} ({self.tts_voice})")
        else:
            logger.warning(f"Unknown anime voice: {voice_name}")
    
    def enable_low_resource_mode(self):
        """Optimize settings for low-spec hardware."""
        self.low_resource_mode = True
        self.screenshot_interval = 60.0  # Reduce screenshot frequency
        self.max_response_tokens_game = 20
        self.max_response_tokens_idle = 60
        self.max_response_tokens_work = 30
        logger.info("Low resource mode enabled")


# Global config instance (lazy-loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global _config
    _config = Config()
    return _config
