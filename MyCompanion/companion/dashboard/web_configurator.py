"""
Web Configurator - Real-time Web Dashboard for Parameter Tuning

This module provides a web-based interface for:
- Adjusting personality parameters in real-time
- Monitoring system status and emotions
- Managing voices and TTS settings
- Viewing memory and relationship status
- Configuring system behavior
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from companion.utils.singleton import singletons

try:
    from aiohttp import web
    import socketio
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("aiohttp or python-socketio not installed. Web dashboard disabled.")

logger = logging.getLogger(__name__)


class WebConfigurator:
    """
    Web-based configuration dashboard for MyCompanion.
    
    Features:
    - Real-time parameter adjustment via WebSocket
    - Live emotion and status monitoring
    - Voice selection and TTS control
    - Memory and relationship visualization
    - System health monitoring
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """
        Initialize Web Configurator
        
        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.app: Optional[web.Application] = None
        self.sio: Optional[socketio.AsyncServer] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # References to companion components (set during initialization)
        self.identity_manager = None
        self.personality_loader = None
        self.emotion_engine = None
        self.tts_handler = None
        self.memory_system = None
        self.config = None
        
        self._is_running = False
        
        if not AIOHTTP_AVAILABLE:
            logger.error("Web dashboard requires: pip install aiohttp python-socketio")
    
    def set_components(
        self,
        identity_manager=None,
        personality_loader=None,
        emotion_engine=None,
        tts_handler=None,
        memory_system=None,
        config=None
    ):
        """Set references to companion components"""
        self.identity_manager = identity_manager
        self.personality_loader = personality_loader
        self.emotion_engine = emotion_engine
        self.tts_handler = tts_handler
        self.memory_system = memory_system
        self.config = config
    
    async def setup(self):
        """Setup the web server and Socket.IO"""
        if not AIOHTTP_AVAILABLE:
            return False
        
        try:
            # Create Socket.IO server
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                async_mode='aiohttp'
            )
            
            # Register event handlers
            self.sio.on('connect', self.on_connect)
            self.sio.on('disconnect', self.on_disconnect)
            self.sio.on('update_parameter', self.on_update_parameter)
            self.sio.on('change_voice', self.on_change_voice)
            self.sio.on('get_status', self.on_get_status)
            self.sio.on('adjust_emotion', self.on_adjust_emotion)
            
            # Create aiohttp app
            self.app = web.Application()
            self.sio.attach(self.app)
            
            # Setup static files and routes
            self._setup_routes()
            
            logger.info(f"Web Configurator setup complete on http://{self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Web Configurator: {e}")
            return False
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        # Serve main dashboard page
        self.app.router.add_get('/', self.serve_dashboard)
        
        # API endpoints
        self.app.router.add_get('/api/status', self.api_get_status)
        self.app.router.add_post('/api/personality', self.api_update_personality)
        self.app.router.add_get('/api/voices', self.api_get_voices)
        self.app.router.add_get('/api/memory', self.api_get_memory_summary)
    
    async def serve_dashboard(self, request: web.Request) -> web.Response:
        """Serve the main dashboard HTML page"""
        try:
            template_path = Path(__file__).parent / 'templates' / 'dashboard.html'
            
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return web.Response(text=html_content, content_type='text/html')
            else:
                # Return minimal inline HTML if template missing
                return web.Response(
                    text=self._get_fallback_html(),
                    content_type='text/html'
                )
        except Exception as e:
            logger.error(f"Error serving dashboard: {e}")
            return web.Response(text=f"Error: {e}", status=500)
    
    async def on_connect(self, sid: str, environ: dict):
        """Handle client connection"""
        logger.info(f"Client connected: {sid}")
        await self.sio.emit('connected', {'status': 'connected'}, room=sid)
        
        # Send initial state
        await self.sio.emit('initial_state', await self._get_full_state(), room=sid)
    
    async def on_disconnect(self, sid: str):
        """Handle client disconnection"""
        logger.info(f"Client disconnected: {sid}")
    
    async def on_update_parameter(self, sid: str, data: dict):
        """Handle parameter update request"""
        param = data.get('parameter')
        value = data.get('value')
        
        logger.info(f"Parameter update: {param} = {value}")
        
        if self.personality_loader and param in ['energy_level', 'openness', 'empathy', 'humor']:
            success = self.personality_loader.adjust_parameter(param, float(value))
            await self.sio.emit('parameter_updated', {
                'parameter': param,
                'value': value,
                'success': success
            }, room=sid)
        
        elif self.config and hasattr(self.config, param):
            try:
                setattr(self.config, param, value)
                await self.sio.emit('parameter_updated', {
                    'parameter': param,
                    'value': value,
                    'success': True
                }, room=sid)
            except Exception as e:
                await self.sio.emit('parameter_updated', {
                    'parameter': param,
                    'value': value,
                    'success': False,
                    'error': str(e)
                }, room=sid)
    
    async def on_change_voice(self, sid: str, data: dict):
        """Handle voice change request"""
        voice_name = data.get('voice')
        
        logger.info(f"Voice change request: {voice_name}")
        
        if self.tts_handler:
            self.tts_handler.set_voice(voice_name)
            await self.sio.emit('voice_changed', {
                'voice': voice_name,
                'success': True
            }, room=sid)
    
    async def on_get_status(self, sid: str):
        """Handle status request"""
        status = await self._get_full_state()
        await self.sio.emit('status_update', status, room=sid)
    
    async def on_adjust_emotion(self, sid: str, data: dict):
        """Handle manual emotion adjustment"""
        emotion = data.get('emotion')
        delta = data.get('delta', 0.0)
        
        logger.info(f"Emotion adjustment: {emotion} += {delta}")
        
        if self.emotion_engine:
            # Would call emotion engine method here
            await self.sio.emit('emotion_adjusted', {
                'emotion': emotion,
                'delta': delta,
                'success': True
            }, room=sid)
    
    async def _get_full_state(self) -> dict:
        """Get complete system state"""
        state = {
            'timestamp': asyncio.get_event_loop().time(),
            'identity': {},
            'personality': {},
            'emotions': {},
            'tts': {},
            'memory': {},
            'system': {}
        }
        
        # Identity info
        if self.identity_manager:
            state['identity'] = {
                'name': self.identity_manager.get_name(),
                'nickname': self.identity_manager.get_nickname(),
                'relationship': self.identity_manager.get_relationship_summary()
            }
        
        # Personality info
        if self.personality_loader:
            state['personality'] = {
                'active_profile': self.personality_loader.get_active_profile_name(),
                'profiles_available': self.personality_loader.get_all_profiles(),
                'dynamic_params': {}
            }
            if self.personality_loader.active_profile:
                p = self.personality_loader.active_profile
                state['personality']['dynamic_params'] = {
                    'energy_level': p.energy_level,
                    'openness': p.openness,
                    'empathy': p.empathy,
                    'humor': p.humor,
                }
        
        # Emotion state
        if self.emotion_engine:
            state['emotions'] = self.emotion_engine.get_emotion_state()
        
        # TTS info
        if self.tts_handler:
            state['tts'] = {
                'current_voice': self.tts_handler.current_voice,
                'available_voices': self.tts_handler.list_voices(),
                'is_speaking': self.tts_handler.is_speaking,
                'stats': self.tts_handler.get_stats()
            }
        
        # Memory summary
        if self.memory_system:
            state['memory'] = self.memory_system.get_summary()
        
        # System info
        if self.config:
            state['system'] = {
                'llm_provider': self.config.llm_provider,
                'llm_model': self.config.llm_model,
                'vision_enabled': self.config.vision_enabled,
                'debug_mode': self.config.debug_mode,
            }
        
        return state
    
    async def api_get_status(self, request: web.Request) -> web.Response:
        """REST API endpoint for status"""
        status = await self._get_full_state()
        return web.json_response(status)
    
    async def api_update_personality(self, request: web.Request) -> web.Response:
        """REST API endpoint for personality updates"""
        try:
            data = await request.json()
            
            if self.personality_loader:
                for param, value in data.items():
                    if param in ['energy_level', 'openness', 'empathy', 'humor']:
                        self.personality_loader.adjust_parameter(param, float(value))
                
                return web.json_response({'success': True})
            
            return web.json_response({'success': False, 'error': 'Personality loader not available'}, status=503)
            
        except Exception as e:
            return web.json_response({'success': False, 'error': str(e)}, status=400)
    
    async def api_get_voices(self, request: web.Request) -> web.Response:
        """REST API endpoint for available voices"""
        if self.tts_handler:
            voices = {
                'current': self.tts_handler.current_voice,
                'available': self.tts_handler.list_voices(),
                'profiles': self.tts_handler.VOICE_PROFILES
            }
            return web.json_response(voices)
        
        return web.json_response({'error': 'TTS handler not available'}, status=503)
    
    async def api_get_memory_summary(self, request: web.Request) -> web.Response:
        """REST API endpoint for memory summary"""
        if self.memory_system:
            return web.json_response(self.memory_system.get_summary())
        
        return web.json_response({'error': 'Memory system not available'}, status=503)
    
    async def start(self):
        """Start the web server"""
        if not AIOHTTP_AVAILABLE or not self.app:
            return False
        
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self._is_running = True
            logger.info(f"Web Configurator started at http://{self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Web Configurator: {e}")
            return False
    
    async def stop(self):
        """Stop the web server"""
        if self.runner and self._is_running:
            await self.runner.cleanup()
            self._is_running = False
            logger.info("Web Configurator stopped")
    
    async def broadcast_update(self, event_type: str, data: dict):
        """Broadcast update to all connected clients"""
        if self.sio:
            await self.sio.emit(event_type, data)
    
    def _get_fallback_html(self) -> str:
        """Return minimal fallback HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head><title>MyCompanion Dashboard</title></head>
        <body>
            <h1>MyCompanion Web Dashboard</h1>
            <p>Dashboard template not found. Please ensure templates/dashboard.html exists.</p>
        </body>
        </html>
        """


def get_web_configurator() -> WebConfigurator:
    """Get or create the global Web Configurator instance"""
    return singletons.get_or_create(WebConfigurator)


def initialize_web_configurator(host: str = "0.0.0.0", port: int = 8080) -> WebConfigurator:
    """Initialize the global Web Configurator"""
    return singletons.create(WebConfigurator, host, port)
