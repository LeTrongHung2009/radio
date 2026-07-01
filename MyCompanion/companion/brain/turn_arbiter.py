"""
brain/turn_arbiter.py
Quản lý lượt nói/nghe (Turn-Taking) và xử lý ngắt lời (Interrupt Handling).
Kết nối mic_agent và tts_handler thông qua Event Bus để Miku có thể:
- Dừng phát TTS khi User nói (interrupt)
- Biết khi nào được phép nói (không chen ngang User)
- Xử lý các tình huống hội thoại tự nhiên
"""
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from enum import Enum, auto

from core.event_bus import Event, event_bus
from companion.utils.singleton import singletons

logger = logging.getLogger("Miku.TurnArbiter")


class TurnState(Enum):
    """Trạng thái lượt trong hội thoại"""
    IDLE = auto()           # Không ai nói
    USER_SPEAKING = auto()  # User đang nói
    MIKU_SPEAKING = auto()  # Miku đang nói
    INTERRUPTED = auto()    # Miku bị ngắt lời


class TurnArbiter:
    """
    Quản lý lượt hội thoại và xử lý ngắt lời.
    
    Responsibilities:
    - Theo dõi trạng thái hội thoại (ai đang nói)
    - Xử lý sự kiện UserSpeaking từ mic_agent
    - Gửi tín hiệu dừng TTS khi bị ngắt lời
    - Quản lý độ trễ trước khi Miku nói (tránh chen ngang)
    - Phát sự kiện cho các module khác biết trạng thái lượt
    """
    
    def __init__(self):
        self._state = TurnState.IDLE
        self._user_speech_start: Optional[datetime] = None
        self._miku_speech_start: Optional[datetime] = None
        self._interrupt_pending = False
        self._speech_queue: list = []  # Queue các câu chờ nói
        
        # Cấu hình
        self.interrupt_threshold = 0.3  # Giây - thời gian User nói để trigger interrupt
        self.response_delay = 0.5  # Giây - trễ trước khi Miku nói (tự nhiên hơn)
        self.min_gap_between_turns = 0.2  # Giây - khoảng cách tối thiểu giữa các lượt
        
        # Callbacks
        self._on_interrupt_callback: Optional[Callable] = None
        
        logger.info("TurnArbiter initialized")
    
    async def initialize(self):
        """Đăng ký lắng nghe sự kiện từ Event Bus"""
        # Lắng nghe User bắt đầu nói
        await event_bus.subscribe("UserSpeaking", self._on_user_started_speaking)
        
        # Lắng nghe User ngừng nói
        await event_bus.subscribe("UserStoppedSpeaking", self._on_user_stopped_speaking)
        
        # Lắng nghe Miku bắt đầu nói
        await event_bus.subscribe("MikuStartedSpeaking", self._on_miku_started_speaking)
        
        # Lắng nghe Miku ngừng nói
        await event_bus.subscribe("MikuStoppedSpeaking", self._on_miku_stopped_speaking)
        
        logger.info("TurnArbiter subscribed to events")
    
    async def _on_user_started_speaking(self, event: Event):
        """
        Xử lý khi User bắt đầu nói.
        Nếu Miku đang nói -> Trigger interrupt ngay lập tức.
        """
        logger.debug(f"User started speaking (current state: {self._state.name})")
        
        self._user_speech_start = datetime.now()
        previous_state = self._state
        
        # Nếu Miku đang nói -> Ngắt lời ngay
        if self._state == TurnState.MIKU_SPEAKING:
            logger.info("⚡ INTERRUPT: User interrupted Miku!")
            self._state = TurnState.INTERRUPTED
            self._interrupt_pending = True
            
            # Phát sự kiện yêu cầu dừng TTS
            await event_bus.publish(Event(
                type="TTSInterrupt",
                source="turn_arbiter",
                payload={
                    "reason": "user_speaking",
                    "timestamp": datetime.now().isoformat()
                },
                priority=3  # Priority cao nhất
            ))
            
            # Gọi callback nếu có
            if self._on_interrupt_callback:
                self._on_interrupt_callback()
        
        elif self._state == TurnState.IDLE:
            self._state = TurnState.USER_SPEAKING
        
        # Phát sự kiện cập nhật trạng thái
        await event_bus.publish(Event(
            type="TurnStateChanged",
            source="turn_arbiter",
            payload={
                "previous_state": previous_state.name,
                "current_state": self._state.name,
                "is_user_speaking": True,
                "is_miku_speaking": False,
                "interrupted": self._interrupt_pending
            }
        ))
    
    async def _on_user_stopped_speaking(self, event: Event):
        """
        Xử lý khi User ngừng nói.
        Chuyển trạng thái về IDLE và kích hoạt queue nếu có câu chờ.
        """
        logger.debug("User stopped speaking")
        
        if self._state == TurnState.USER_SPEAKING:
            speech_duration = (datetime.now() - self._user_speech_start).total_seconds()
            logger.debug(f"User spoke for {speech_duration:.2f}s")
            
            self._state = TurnState.IDLE
            self._user_speech_start = None
            
            # Phát sự kiện
            await event_bus.publish(Event(
                type="TurnStateChanged",
                source="turn_arbiter",
                payload={
                    "previous_state": TurnState.USER_SPEAKING.name,
                    "current_state": TurnState.IDLE.name,
                    "is_user_speaking": False,
                    "is_miku_speaking": False,
                    "speech_duration": speech_duration
                }
            ))
            
            # Kiểm tra queue và nói câu tiếp theo nếu có
            await self._process_speech_queue()
    
    async def _on_miku_started_speaking(self, event: Event):
        """Xử lý khi Miku bắt đầu nói"""
        logger.debug("Miku started speaking")
        
        if self._state == TurnState.IDLE:
            self._state = TurnState.MIKU_SPEAKING
            self._miku_speech_start = datetime.now()
            self._interrupt_pending = False
            
            await event_bus.publish(Event(
                type="TurnStateChanged",
                source="turn_arbiter",
                payload={
                    "previous_state": TurnState.IDLE.name,
                    "current_state": TurnState.MIKU_SPEAKING.name,
                    "is_user_speaking": False,
                    "is_miku_speaking": True
                }
            ))
    
    async def _on_miku_stopped_speaking(self, event: Event):
        """Xử lý khi Miku ngừng nói (tự nhiên hoặc bị ngắt)"""
        logger.debug(f"Miku stopped speaking (interrupted: {self._interrupt_pending})")
        
        previous_state = self._state
        self._state = TurnState.IDLE
        self._miku_speech_start = None
        
        if self._interrupt_pending:
            logger.info("✓ Interrupt completed")
            self._interrupt_pending = False
        
        await event_bus.publish(Event(
            type="TurnStateChanged",
            source="turn_arbiter",
            payload={
                "previous_state": previous_state.name,
                "current_state": TurnState.IDLE.name,
                "is_user_speaking": False,
                "is_miku_speaking": False,
                "was_interrupted": previous_state == TurnState.INTERRUPTED
            }
        ))
    
    async def request_to_speak(self, text: str, priority: int = 1) -> bool:
        """
        Yêu cầu Miku nói một câu.
        
        Args:
            text: Nội dung cần nói
            priority: Độ ưu tiên (0: thấp, 1: bình thường, 2: cao)
        
        Returns:
            True nếu được phép nói ngay, False nếu phải chờ vào queue
        """
        # Nếu đang có interrupt pending, bỏ qua
        if self._interrupt_pending:
            logger.debug("Skipping speak request during interrupt")
            return False
        
        # Nếu User đang nói, đưa vào queue
        if self._state == TurnState.USER_SPEAKING:
            logger.debug(f"Queuing speech (User is speaking): {text[:30]}...")
            self._speech_queue.append({
                "text": text,
                "priority": priority,
                "queued_at": datetime.now()
            })
            # Sort queue by priority
            self._speech_queue.sort(key=lambda x: -x["priority"])
            return False
        
        # Nếu Miku đang nói, đưa vào queue (trừ khi priority cao)
        if self._state == TurnState.MIKU_SPEAKING:
            if priority >= 2:  # High priority can interrupt own queue
                logger.debug(f"High priority speech queued: {text[:30]}...")
            else:
                logger.debug(f"Queuing speech (Miku is speaking): {text[:30]}...")
            
            self._speech_queue.append({
                "text": text,
                "priority": priority,
                "queued_at": datetime.now()
            })
            self._speech_queue.sort(key=lambda x: -x["priority"])
            return False
        
        # IDLE - Có thể nói ngay (với delay nhỏ cho tự nhiên)
        if self._state == TurnState.IDLE:
            logger.debug(f"Granted permission to speak: {text[:30]}...")
            
            # Delay nhỏ trước khi nói để tạo cảm giác tự nhiên
            await asyncio.sleep(self.response_delay)
            
            # Kiểm tra lại trạng thái sau delay
            if self._state != TurnState.IDLE:
                logger.debug("State changed during delay, re-queuing")
                self._speech_queue.append({
                    "text": text,
                    "priority": priority,
                    "queued_at": datetime.now()
                })
                return False
            
            return True
        
        return False
    
    async def _process_speech_queue(self):
        """Xử lý queue lời nói khi đến lượt"""
        if not self._speech_queue or self._state != TurnState.IDLE:
            return
        
        # Lấy câu có priority cao nhất
        next_speech = self._speech_queue.pop(0)
        
        logger.info(f"Processing queued speech: {next_speech['text'][:30]}...")
        
        # Phát sự kiện yêu cầu TTS nói
        await event_bus.publish(Event(
            type="TTSSpeakRequest",
            source="turn_arbiter",
            payload={
                "text": next_speech["text"],
                "priority": next_speech["priority"],
                "from_queue": True
            },
            priority=next_speech["priority"]
        ))
    
    def set_interrupt_callback(self, callback: Callable):
        """Đặt callback khi xảy ra interrupt"""
        self._on_interrupt_callback = callback
        logger.info("Interrupt callback registered")
    
    def get_state(self) -> Dict[str, Any]:
        """Lấy trạng thái hiện tại của TurnArbiter"""
        return {
            "state": self._state.name,
            "is_user_speaking": self._state == TurnState.USER_SPEAKING,
            "is_miku_speaking": self._state == TurnState.MIKU_SPEAKING,
            "interrupt_pending": self._interrupt_pending,
            "queue_length": len(self._speech_queue),
            "config": {
                "interrupt_threshold": self.interrupt_threshold,
                "response_delay": self.response_delay,
                "min_gap_between_turns": self.min_gap_between_turns
            }
        }
    
    async def shutdown(self):
        """Dọn dẹp khi shutdown"""
        logger.info("TurnArbiter shutting down")
        self._speech_queue.clear()
        self._state = TurnState.IDLE


def get_turn_arbiter() -> TurnArbiter:
    """Get global turn_arbiter instance"""
    return singletons.get_or_raise(TurnArbiter)


def initialize_turn_arbiter() -> TurnArbiter:
    """Initialize global turn_arbiter"""
    return singletons.create(TurnArbiter)
