"""
expression/avatar_renderer.py
Render mô hình 3D avatar (VRM/Live2D) trong cửa sổ PyQt6 sử dụng QWebEngineView.
Hiển thị avatar dạng trong suốt, click-through để không cản trở thao tác người dùng.

Dependencies:
- PyQt6
- PyQt6-WebEngine
- Three.js (trong HTML)
"""
import os
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

# Try to import websockets for lip-sync communication
try:
    import asyncio
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    import json

logger = logging.getLogger("Miku.AvatarRenderer")


class AvatarWebPage(QWebEnginePage):
    """Custom WebEngine page for avatar rendering"""
    
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        # Only allow local file navigation
        if url.scheme() == 'file':
            return True
        return False


class AvatarRenderer(QWidget):
    """
    Widget hiển thị avatar 3D sử dụng QWebEngineView.
    
    Features:
    - Hiển thị HTML/Three.js avatar với nền trong suốt
    - Always-on-top, click-through (không chặn input)
    - WebSocket communication để đồng bộ lip-sync
    - Hỗ trợ cảm xúc và trạng thái animation
    """
    
    # Signals
    avatar_ready = pyqtSignal()
    avatar_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.websocket: Optional[Any] = None
        self.ws_connected = False
        self.avatar_html_path: Optional[str] = None
        
        # Setup UI
        self._setup_ui()
        
        # WebSocket server for lip-sync
        self.ws_server = None
        self.ws_task = None
        
        logger.info("AvatarRenderer initialized")
    
    def _setup_ui(self):
        """Thiết lập giao diện widget"""
        # Window flags cho transparent, click-through, always-on-top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        # Click-through: Allow mouse events to pass through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # WebEngine View
        self.web_view = QWebEngineView(self)
        
        # Configure WebGL settings
        profile = self.web_view.page().profile()
        profile.setHttpUserAgent("MikuAvatar/1.0")
        
        # Set background transparent
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        # Disable context menu
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        layout.addWidget(self.web_view)
        
        # Resize to reasonable size (can be adjusted)
        self.resize(400, 600)
        
        # Position in bottom-right corner (default)
        self._position_avatar()
    
    def _position_avatar(self):
        """Đặt avatar ở góc phải dưới màn hình"""
        screen = QApplication.primaryScreen().geometry()
        
        # Position: bottom-right, with some margin
        margin_x = 50
        margin_y = 50
        
        x = screen.width() - self.width() - margin_x
        y = screen.height() - self.height() - margin_y
        
        self.move(x, y)
    
    async def _websocket_handler(self, websocket, path):
        """Xử lý WebSocket connection từ avatar HTML"""
        logger.info("Avatar WebSocket connected")
        self.ws_connected = True
        
        try:
            async for message in websocket:
                data = json.loads(message)
                logger.debug(f"Received from avatar: {data}")
                
                # Handle messages from avatar if needed
                if data.get('type') == 'ready':
                    self.avatar_ready.emit()
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Avatar WebSocket disconnected")
        finally:
            self.ws_connected = False
    
    async def start_websocket_server(self, port: int = 8765):
        """Khởi động WebSocket server để giao tiếp với avatar"""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets not available, lip-sync disabled")
            return
        
        try:
            self.ws_server = await websockets.serve(
                self._websocket_handler,
                "localhost",
                port
            )
            logger.info(f"WebSocket server started on ws://localhost:{port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def send_to_avatar(self, data: Dict[str, Any]):
        """Gửi dữ liệu đến avatar qua WebSocket"""
        if not self.ws_connected or not self.websocket:
            return
        
        try:
            await self.websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to send to avatar: {e}")
    
    def load_avatar(self, html_path: Optional[str] = None):
        """
        Load avatar HTML file.
        
        Args:
            html_path: Đường dẫn đến file HTML. Nếu None, dùng file mặc định.
        """
        if html_path is None:
            # Default path
            default_path = Path(__file__).parent / "assets" / "avatar.html"
            if default_path.exists():
                self.avatar_html_path = str(default_path.absolute())
            else:
                logger.error(f"Default avatar HTML not found at {default_path}")
                self.avatar_error.emit("Avatar HTML not found")
                return
        else:
            self.avatar_html_path = Path(html_path).absolute()
            if not self.avatar_html_path.exists():
                logger.error(f"Avatar HTML not found at {self.avatar_html_path}")
                self.avatar_error.emit(f"File not found: {html_path}")
                return
        
        # Load the HTML file
        file_url = QUrl.fromLocalFile(self.avatar_html_path)
        logger.info(f"Loading avatar from: {file_url.toString()}")
        
        self.web_view.load(file_url)
        self.web_view.show()
    
    def set_emotion(self, emotion: str):
        """
        Đặt cảm xúc cho avatar.
        
        Args:
            emotion: one of ['neutral', 'happy', 'sad', 'angry', 'surprised', 'excited']
        """
        self._send_command('emotion', {'emotion': emotion})
        logger.debug(f"Set emotion: {emotion}")
    
    def set_state(self, state: str):
        """
        Đặt trạng thái animation.
        
        Args:
            state: one of ['idle', 'speaking', 'listening', 'thinking']
        """
        self._send_command('state', {'state': state})
        logger.debug(f"Set state: {state}")
    
    def set_lip_sync(self, openness: float):
        """
        Đồng bộ khẩu hình miệng.
        
        Args:
            openness: Độ mở miệng (0.0 - 1.0)
        """
        self._send_command('lip_sync', {'openness': max(0.0, min(1.0, openness))})
    
    def _send_command(self, cmd_type: str, payload: Dict[str, Any]):
        """Gửi command đến avatar"""
        # For now, just log - actual implementation would use WebSocket
        logger.debug(f"Command to avatar: {cmd_type} -> {payload}")
    
    def show_event(self, event):
        """Handle show event to position correctly"""
        super().showEvent(event)
        self._position_avatar()
    
    def closeEvent(self, event):
        """Cleanup on close"""
        if self.ws_server:
            self.ws_server.close()
        super().closeEvent(event)
    
    async def shutdown(self):
        """Dọn dẹp khi shutdown"""
        logger.info("AvatarRenderer shutting down")
        if self.ws_server:
            self.ws_server.close()
            await self.ws_server.wait_closed()


# Singleton instance
_avatar_renderer: Optional[AvatarRenderer] = None


def get_avatar_renderer() -> AvatarRenderer:
    """Get global avatar renderer instance"""
    global _avatar_renderer
    if _avatar_renderer is None:
        raise RuntimeError("AvatarRenderer not initialized!")
    return _avatar_renderer


def initialize_avatar_renderer(parent=None) -> AvatarRenderer:
    """Initialize global avatar renderer"""
    global _avatar_renderer
    _avatar_renderer = AvatarRenderer(parent)
    return _avatar_renderer
