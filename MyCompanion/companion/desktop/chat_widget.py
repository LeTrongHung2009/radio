"""
Desktop Chat Widget - PyQt6 transparent always-on-top chat interface
Provides a minimal, elegant chat box for quick text interaction with Miku
"""
import sys
import asyncio
from typing import Optional, Callable
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPoint, QRect, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QPixmap, QPainter, QBrush, 
    QPen, QLinearGradient, QAction
)

import logging
logger = logging.getLogger(__name__)


class TransparentButton(QPushButton):
    """Custom styled button with hover effects"""
    
    def __init__(self, text: str = "", icon_path: Optional[str] = None):
        super().__init__(text)
        
        # Style configuration
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Apply stylesheet
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)


class ChatInput(QTextEdit):
    """Custom text input with auto-resize and placeholder"""
    
    def __init__(self):
        super().__init__()
        
        self.setPlaceholderText("Type to Miku... (Enter to send)")
        self.setMaximumHeight(80)
        self.setMinimumHeight(40)
        
        # Style
        self.setStyleSheet("""
            QTextEdit {
                background-color: rgba(30, 30, 40, 0.85);
                border: 1px solid rgba(100, 100, 150, 0.3);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.95);
                padding: 8px;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTextEdit:focus {
                border: 1px solid rgba(150, 100, 200, 0.6);
                background-color: rgba(35, 35, 50, 0.9);
            }
        """)
        
        # Remove default frame
        self.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Enable enter to send
        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle Enter key"""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Return and not key_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.send_signal.emit()
                return True
        return super().eventFilter(obj, event)
    
    send_signal = pyqtSignal()


class ChatWidget(QWidget):
    """
    Main desktop chat widget
    
    Features:
    - Frameless, transparent window
    - Always on top
    - Draggable
    - Minimalist design
    - System tray integration
    """
    
    # Signals
    message_sent = pyqtSignal(str)  # Emitted when user sends message
    widget_hidden = pyqtSignal()
    widget_shown = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Window configuration
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Initial size and position
        self.default_width = 350
        self.default_height = 120
        self.resize(self.default_width, self.default_height)
        
        # Position at top-right of screen
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.default_width - 20, 20)
        
        # Make draggable
        self.drag_position = QPoint()
        self.dragging = False
        
        # Setup UI
        self._setup_ui()
        
        # System tray
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self._setup_tray()
        
        # Animation for show/hide
        self.opacity_effect = QGraphicsDropShadowEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # State
        self.is_visible = True
        self.typing_indicator = False
        
        logger.info("Chat widget initialized")
    
    def _setup_ui(self):
        """Setup widget UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Header bar (for dragging and controls)
        header = self._create_header()
        layout.addWidget(header)
        
        # Input area
        self.input_field = ChatInput()
        self.input_field.send_signal.connect(self._on_send)
        layout.addWidget(self.input_field)
        
        # Status indicator
        self.status_label = QLabel("Miku is ready")
        self.status_label.setStyleSheet("""
            color: rgba(150, 200, 255, 0.8);
            font-size: 11px;
            padding-left: 4px;
        """)
        layout.addWidget(self.status_label)
    
    def _create_header(self) -> QWidget:
        """Create draggable header with control buttons"""
        header = QWidget()
        header.setFixedHeight(30)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)
        
        # Title/Logo area (for dragging)
        title = QLabel("🌸 Miku")
        title.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: bold;
            padding-left: 5px;
        """)
        title.setCursor(Qt.CursorShape.SizeAllCursor)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Control buttons
        self.minimize_btn = TransparentButton("−")
        self.minimize_btn.clicked.connect(self._minimize)
        header_layout.addWidget(self.minimize_btn)
        
        self.close_btn = TransparentButton("×")
        self.close_btn.clicked.connect(self._hide_widget)
        header_layout.addWidget(self.close_btn)
        
        return header
    
    def _setup_tray(self):
        """Setup system tray icon"""
        try:
            self.tray_icon = QSystemTrayIcon(self)
            
            # Create simple icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(QColor(100, 200, 255)))
            painter.drawEllipse(2, 2, 28, 28)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "M")
            painter.end()
            
            icon = QIcon(pixmap)
            self.tray_icon.setIcon(icon)
            
            # Context menu
            tray_menu = QMenu()
            
            show_action = QAction("Show Miku", self)
            show_action.triggered.connect(self.show_widget)
            tray_menu.addAction(show_action)
            
            hide_action = QAction("Hide Miku", self)
            hide_action.triggered.connect(self.hide_widget)
            tray_menu.addAction(hide_action)
            
            tray_menu.addSeparator()
            
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(self._quit_application)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.setToolTip("Miku - AI Companion")
            self.tray_icon.activated.connect(self._tray_activated)
            self.tray_icon.show()
            
            logger.info("System tray icon created")
            
        except Exception as e:
            logger.warning(f"System tray setup failed: {e}")
            self.tray_icon = None
    
    def _tray_activated(self, reason):
        """Handle tray icon clicks"""
        from PyQt6.QSystemTrayIcon import ActivationReason
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()
    
    def mousePressEvent(self, event):
        """Start dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.dragging = True
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle dragging"""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Stop dragging"""
        self.dragging = False
        super().mouseReleaseEvent(event)
    
    def _on_send(self):
        """Handle message send"""
        text = self.input_field.toPlainText().strip()
        if text:
            self.message_sent.emit(text)
            self.input_field.clear()
            self.set_typing_indicator(True)
    
    def set_typing_indicator(self, typing: bool):
        """Show/hide typing indicator"""
        self.typing_indicator = typing
        if typing:
            self.status_label.setText("Miku is thinking...")
            self.input_field.setEnabled(False)
        else:
            self.status_label.setText("Miku is ready")
            self.input_field.setEnabled(True)
            self.input_field.setFocus()
    
    def add_response(self, text: str):
        """Display AI response (could be shown in a popup or subtitle)"""
        # For now, just update status
        self.status_label.setText(f"Last: {text[:50]}...")
    
    def toggle_visibility(self):
        """Toggle widget visibility"""
        if self.is_visible:
            self.hide_widget()
        else:
            self.show_widget()
    
    def show_widget(self):
        """Show widget with animation"""
        self.show()
        self.is_visible = True
        self.widget_shown.emit()
        logger.debug("Widget shown")
    
    def hide_widget(self):
        """Hide widget"""
        self.hide()
        self.is_visible = False
        self.widget_hidden.emit()
        logger.debug("Widget hidden")
    
    def _minimize(self):
        """Minimize to tray"""
        self.hide_widget()
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Miku",
                "I'm still here! Double-click tray icon to show me.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
    
    def _hide_widget(self):
        """Hide widget (alias)"""
        self.hide_widget()
    
    def _quit_application(self):
        """Quit application"""
        QApplication.quit()
    
    def closeEvent(self, event):
        """Handle close event"""
        event.ignore()  # Don't actually close, just hide
        self.hide_widget()


class OverlayManager:
    """Manages multiple overlay widgets"""
    
    def __init__(self):
        self.widgets = []
    
    def add_widget(self, widget: ChatWidget):
        """Add widget to management"""
        self.widgets.append(widget)
    
    def hide_all(self):
        """Hide all managed widgets"""
        for widget in self.widgets:
            widget.hide_widget()
    
    def show_all(self):
        """Show all managed widgets"""
        for widget in self.widgets:
            widget.show_widget()
    
    def get_stats(self) -> dict:
        """Get overlay statistics"""
        return {
            'total_widgets': len(self.widgets),
            'visible_count': sum(1 for w in self.widgets if w.is_visible),
            'hidden_count': sum(1 for w in self.widgets if not w.is_visible)
        }


# Test function
def test_widget():
    """Test the chat widget standalone"""
    app = QApplication(sys.argv)
    
    widget = ChatWidget()
    widget.show()
    
    # Connect signal for testing
    def on_message(text):
        print(f"Message sent: {text}")
        widget.add_response("Got it!")
        widget.set_typing_indicator(False)
    
    widget.message_sent.connect(on_message)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_widget()
