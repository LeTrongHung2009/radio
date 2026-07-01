"""
Media Watcher - Monitor media playback on system
Detects currently playing music, videos, etc.
"""
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class MediaWatcher:
    """
    Monitors media playback across applications
    
    Features:
    - Detect active media player
    - Get now playing information
    - Low CPU usage polling
    """
    
    def __init__(self):
        self.last_check = 0
        self.current_media: Optional[Dict] = None
        
        logger.info("Media watcher initialized")
    
    def get_now_playing(self) -> Optional[str]:
        """
        Get currently playing media
        
        Returns:
            "Artist - Title" or None if nothing playing
        """
        try:
            # Try Windows API for media control
            import ctypes
            from ctypes import wintypes
            
            # This is a simplified version - full implementation would use
            # Windows.Media.Control APIs or check specific app windows
            
            # Check common media processes
            import psutil
            
            media_processes = {
                'spotify.exe': 'Spotify',
                'vlc.exe': 'VLC',
                'firefox.exe': 'Firefox',
                'chrome.exe': 'Chrome',
                'msedge.exe': 'Edge',
            }
            
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name'].lower()
                    for proc_name, app_name in media_processes.items():
                        if proc_name in name:
                            # Found media app
                            # Would need deeper integration to get actual track info
                            return f"{app_name} (active)"
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Media detection failed: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get watcher statistics"""
        return {
            'current_media': self.current_media,
            'enabled': True
        }
