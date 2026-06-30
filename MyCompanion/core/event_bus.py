"""
core/event_bus.py
Hệ thống Pub/Sub (Publish-Subscribe) nội bộ.
Đóng vai trò là hệ thần kinh trung ương, cho phép các module giao tiếp bất đồng bộ mà không cần biết nhau trực tiếp.
"""
import asyncio
import logging
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger("Miku.EventBus")

@dataclass
class Event:
    """Cấu trúc dữ liệu chuẩn cho mọi sự kiện trong hệ thống."""
    type: str
    source: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 0  # 0: Thấp, 1: Trung bình, 2: Cao, 3: Khẩn cấp (Interrupt)
    
    def __repr__(self):
        return f"Event(type={self.type}, source={self.source}, id={self.event_id})"

class EventBus:
    """
    Central Event Bus.
    Cho phép các module đăng ký lắng nghe (subscribe) và gửi sự kiện (publish).
    Hỗ trợ xử lý bất đồng bộ và ưu tiên sự kiện.
    """
    _instance: Optional['EventBus'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._queue = asyncio.PriorityQueue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._initialized = True
        logger.info("EventBus initialized.")

    async def start(self):
        """Khởi động vòng lặp xử lý sự kiện."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("EventBus processing loop started.")

    async def stop(self):
        """Dừng vòng lặp xử lý."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped.")

    async def publish(self, event: Event):
        """Gửi một sự kiện vào hàng đợi."""
        # Đảo ngược priority để số lớn ưu tiên hơn (PriorityQueue lấy số nhỏ trước)
        priority_score = -event.priority
        await self._queue.put((priority_score, event.timestamp, event))
        logger.debug(f"Published event: {event}")

    async def subscribe(self, event_type: str, callback: Callable):
        """Đăng ký hàm xử lý cho một loại sự kiện."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type}")

    async def unsubscribe(self, event_type: str, callback: Callable):
        """Hủy đăng ký."""
        async with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(callback)

    async def _process_loop(self):
        """Vòng lặp chính: Lấy sự kiện và gọi các handler."""
        while self._running:
            try:
                # Lấy sự kiện với timeout để kiểm tra flag _running
                try:
                    _, _, event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

                # Xử lý sự kiện
                await self._dispatch(event)
                self._queue.task_done()

            except Exception as e:
                logger.error(f"Error in EventBus loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _dispatch(self, event: Event):
        """Gửi sự kiện đến các subscriber phù hợp."""
        handlers = self._subscribers.get(event.type, [])
        
        # Gửi cho các handler đăng ký loại cụ thể
        tasks = [handler(event) for handler in handlers]
        
        # Gửi cho các handler đăng ký '*' (tất cả sự kiện - dùng cho logging/debug)
        global_handlers = self._subscribers.get('*', [])
        tasks.extend([handler(event) for handler in global_handlers])

        if tasks:
            # Chạy song song nhưng có giới hạn để không nghẽn hệ thống
            await asyncio.gather(*tasks, return_exceptions=True)

# Singleton instance
event_bus = EventBus()
