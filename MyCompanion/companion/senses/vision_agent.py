"""
Vision Agent - Screen capture and analysis
Lightweight screen monitoring for context awareness
"""
import asyncio
import logging
from typing import Optional, bytes
from datetime import datetime

logger = logging.getLogger(__name__)


class VisionAgent:
    """
    Screen capture and basic analysis
    
    Features:
    - Periodic screen capture
    - Change detection
    - Lightweight processing for AMD GPU compatibility
    """
    
    def __init__(self):
        self.last_capture_time = 0
        self.last_capture_hash = ""
        self.capture_count = 0
        
        logger.info("Vision agent initialized")
    
    async def capture_screen(self) -> Optional[bytes]:
        """
        Capture current screen
        
        Returns:
            Image bytes or None if failed
        """
        try:
            # Try using mss (fast, cross-platform)
            try:
                import mss
                import mss.tools
                
                with mss.mss() as sct:
                    # Capture primary monitor
                    monitor = sct.monitors[0]  # Full desktop
                    screenshot = sct.grab(monitor)
                    
                    # Convert to PNG bytes
                    img_data = mss.tools.to_png(screenshot.rgb, screenshot.size)
                    
                    self.capture_count += 1
                    self.last_capture_time = datetime.now().timestamp()
                    
                    logger.debug(f"Screen captured ({len(img_data)} bytes)")
                    return img_data
                    
            except ImportError:
                # Fallback to PIL
                logger.debug("mss not available, using PIL fallback")
                from PIL import ImageGrab
                
                img = ImageGrab.grab()
                import io
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                
                self.capture_count += 1
                self.last_capture_time = datetime.now().timestamp()
                
                return img_bytes.getvalue()
                
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None
    
    def get_stats(self) -> dict:
        """Get vision agent statistics"""
        return {
            'capture_count': self.capture_count,
            'last_capture': self.last_capture_time,
            'enabled': True
        }


# Convenience function
async def quick_capture() -> Optional[bytes]:
    """Quick screen capture"""
    agent = VisionAgent()
    return await agent.capture_screen()
