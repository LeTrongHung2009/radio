"""
PyQt6 Chat Widget

Minimal, frameless, alpha-transparent, always-on-top chat widget.
Supports smooth mouse-drag repositioning and hotkey toggle.
"""

import logging
from typing import Optional

from PyQt6.QtCore import (
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
    Qt,
    pyqtSignal,
    pyqtSlot,
    QSize,
)
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class _ChatBubble(QWidget):
    """Single chat message bubble."""

    def __init__(self, text: str, is_ai: bool, emotion: str = "neutral", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Noto Sans", 10))

        if is_ai:
            bg = self._emotion_color(emotion)
            label.setStyleSheet(
                f"background-color: {bg}; color: #fff; "
                f"border-radius: 12px; padding: 8px 12px;"
            )
        else:
            label.setStyleSheet(
                "background-color: #3a3f4b; color: #e0e0e0; "
                "border-radius: 12px; padding: 8px 12px;"
            )

        layout.addWidget(label)

    @staticmethod
    def _emotion_color(emotion: str) -> str:
        colors = {
            "neutral": "#5865f2",
            "happy": "#57a64a",
            "sad": "#6272a4",
            "angry": "#e74c3c",
            "excited": "#f39c12",
            "curious": "#9b59b6",
            "concerned": "#e67e22",
            "playful": "#e91e63",
            "thoughtful": "#607d8b",
            "surprised": "#ff5722",
            "bored": "#78909c",
            "smug": "#8e44ad",
            "embarrassed": "#e8847c",
        }
        return colors.get(emotion, "#5865f2")


class ChatWidget(QWidget):
    """
    Frameless, transparent, always-on-top chat overlay.

    Features:
      - Drag to reposition
      - Ctrl+Shift+M to toggle visibility
      - Smooth slide animations
      - Auto-scroll on new messages
    """

    message_sent = pyqtSignal(str)

    WIDTH = 360
    HEIGHT = 480
    MARGIN = 20

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self._drag_pos: Optional[QPoint] = None
        self._visible = True

        self._build_ui()
        self._setup_shortcuts()

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.width() - self.WIDTH - self.MARGIN, geo.height() - self.HEIGHT - self.MARGIN)

    def _build_ui(self) -> None:
        self._container = QWidget(self)
        self._container.setStyleSheet(
            "background-color: rgba(30, 30, 40, 220); border-radius: 16px;"
        )
        self._container.setGeometry(0, 0, self.WIDTH, self.HEIGHT)

        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Title bar
        title = QLabel("MyCompanion")
        title.setFont(QFont("Noto Sans", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #b0b8ff; padding: 4px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Chat area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical { background: #555; border-radius: 2px; }"
        )
        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_layout.setSpacing(6)
        self._chat_layout.addStretch()
        self._scroll.setWidget(self._chat_container)
        main_layout.addWidget(self._scroll, 1)

        # Input strip
        self._input = QLineEdit()
        self._input.setPlaceholderText("Nhập tin nhắn...")
        self._input.setFont(QFont("Noto Sans", 10))
        self._input.setStyleSheet(
            "QLineEdit { background: #2a2d38; color: #e0e0e0; "
            "border: 1px solid #444; border-radius: 10px; padding: 8px 12px; }"
            "QLineEdit:focus { border-color: #5865f2; }"
        )
        self._input.returnPressed.connect(self._on_send)
        main_layout.addWidget(self._input)

    def _setup_shortcuts(self) -> None:
        toggle = QShortcut(QKeySequence("Ctrl+Shift+M"), self)
        toggle.activated.connect(self.toggle_visibility)

    def add_message(self, text: str, is_ai: bool, emotion: str = "neutral") -> None:
        bubble = _ChatBubble(text, is_ai, emotion, self._chat_container)
        # Insert before the stretch
        count = self._chat_layout.count()
        self._chat_layout.insertWidget(count - 1, bubble)
        # Auto-scroll
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

    @pyqtSlot()
    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_message(text, is_ai=False)
        self.message_sent.emit(text)

    def toggle_visibility(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()
        self._visible = not self._visible

    def slide_to(self, pos: QPoint, duration: int = 400) -> None:
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(duration)
        anim.setStartValue(self.pos())
        anim.setEndValue(pos)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
        self._slide_anim = anim  # prevent GC

    # --- Drag support ---
    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        self._drag_pos = None
        event.accept()
