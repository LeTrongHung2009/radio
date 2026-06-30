"""
Activity Monitor - Giám sát hoạt động người dùng
Phát hiện khi user rời khỏi máy, chuyển ứng dụng, hoặc idle.
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger("Miku.ActivityMonitor")

@dataclass
class ActivityEvent:
    event_type: str  # 'idle_start', 'idle_end', 'app_switch', 'mouse_move', 'key_press'
    timestamp: float
    details: Optional[Dict[str, Any]] = None

class ActivityMonitor:
    """
    Theo dõi trạng thái hoạt động của người dùng.
    - Phát hiện thời gian idle (không di chuyển chuột/gõ phím).
    - Phát hiện chuyển đổi ứng dụng đang focus.
    - Gửi sự kiện cho Bot để kích hoạt Boredom Protocol hoặc Welcome Back.
    """
    
    def __init__(self, idle_threshold_seconds: int = 300):  # 5 phút
        self.idle_threshold = idle_threshold_seconds
        self.last_activity_time = time.time()
        self.is_idle = False
        self.current_app: Optional[str] = None
        self.event_callbacks: list[Callable[[ActivityEvent], None]] = []
        self.is_running = False
        self._check_interval = 2.0  # Kiểm tra mỗi 2 giây

    def register_callback(self, callback: Callable[[ActivityEvent], None]):
        """Đăng ký hàm callback để nhận sự kiện hoạt động."""
        self.event_callbacks.append(callback)
        logger.debug("Activity callback registered.")

    async def start(self):
        """Khởi động vòng lặp giám sát."""
        self.is_running = True
        self.last_activity_time = time.time()
        logger.info(f"Activity monitor started. Idle threshold: {self.idle_threshold}s")
        
        while self.is_running:
            try:
                await self._check_activity()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in activity monitoring: {e}", exc_info=True)
                await asyncio.sleep(5)

    def stop(self):
        """Dừng giám sát."""
        self.is_running = False
        logger.info("Activity monitor stopped.")

    async def _check_activity(self):
        """Kiểm tra trạng thái hoạt động và phát hiện thay đổi."""
        current_time = time.time()
        
        # 1. Kiểm tra thời gian idle
        time_since_activity = current_time - self.last_activity_time
        
        if time_since_activity >= self.idle_threshold and not self.is_idle:
            # Chuyển sang trạng thái idle
            self.is_idle = True
            logger.info(f"User is IDLE for {time_since_activity:.1f}s")
            await self._dispatch_event(ActivityEvent(
                event_type='idle_start',
                timestamp=current_time,
                details={'idle_duration': 0}
            ))
            
        elif time_since_activity < self.idle_threshold and self.is_idle:
            # User quay lại
            self.is_idle = False
            idle_duration = time_since_activity
            logger.info(f"User returned after {idle_duration:.1f}s of idle time.")
            await self._dispatch_event(ActivityEvent(
                event_type='idle_end',
                timestamp=current_time,
                details={'idle_duration': idle_duration}
            ))

        # 2. Kiểm tra ứng dụng đang focus
        current_focus = self._get_foreground_app()
        if current_focus != self.current_app:
            old_app = self.current_app
            self.current_app = current_focus
            logger.info(f"App switched: {old_app} -> {current_focus}")
            await self._dispatch_event(ActivityEvent(
                event_type='app_switch',
                timestamp=current_time,
                details={'from': old_app, 'to': current_focus}
            ))

    async def _dispatch_event(self, event: ActivityEvent):
        """Gửi sự kiện đến tất cả các callback đã đăng ký."""
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in activity callback: {e}")

    def _get_foreground_app(self) -> Optional[str]:
        """Lấy tên ứng dụng đang focus."""
        try:
            # Linux: sử dụng xprop hoặc wmctrl
            import subprocess
            result = subprocess.run(
                ['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                # Lấy window ID
                output = result.stdout.strip()
                if '#x' in output:
                    window_id = output.split('#x')[1].strip()
                    # Lấy thông tin window
                    info_result = subprocess.run(
                        ['wmctrl', '-lG'],
                        capture_output=True, text=True, timeout=2
                    )
                    if info_result.returncode == 0:
                        for line in info_result.stdout.splitlines():
                            if window_id in line:
                                parts = line.split(None, 4)
                                if len(parts) > 4:
                                    return parts[4]  # Tên cửa sổ
            return "Unknown"
        except FileNotFoundError:
            # Nếu không có xprop/wmctrl, thử cách khác hoặc trả về Unknown
            logger.warning("xprop or wmctrl not found. Install x11-utils and wmctrl for better app detection.")
            return "Unknown (Install xprop)"
        except Exception as e:
            logger.debug(f"Could not detect foreground app: {e}")
            return "Unknown"

    def record_user_activity(self):
        """Gọi hàm này khi phát hiện hoạt động từ user (mouse, keyboard)."""
        self.last_activity_time = time.time()
        
        # Nếu đang idle mà có hoạt động, đánh dấu ngay
        if self.is_idle:
            self.is_idle = False
            asyncio.create_task(self._dispatch_event(ActivityEvent(
                event_type='idle_end',
                timestamp=time.time(),
                details={'reason': 'user_input_detected'}
            )))

    def get_status(self) -> Dict[str, Any]:
        """Trả về trạng thái hiện tại của activity monitor."""
        current_idle_time = time.time() - self.last_activity_time
        return {
            'is_idle': self.is_idle,
            'current_app': self.current_app,
            'idle_time_seconds': current_idle_time,
            'threshold_seconds': self.idle_threshold,
            'last_activity_ago': current_idle_time
        }

activity_monitor_instance = ActivityMonitor()
