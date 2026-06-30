"""
Notification System - Hệ thống thông báo Desktop
Gửi thông báo hệ thống cho Miku về các sự kiện quan trọng.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import subprocess
import os

logger = logging.getLogger("Miku.NotificationSystem")

@dataclass
class Notification:
    title: str
    message: str
    urgency: str  # 'low', 'normal', 'critical'
    icon: Optional[str] = None
    timeout: int = 5000  # ms

class NotificationSystem:
    """
    Gửi thông báo desktop sử dụng hệ thống notification của OS.
    Trên Linux: sử dụng notify-send (libnotify).
    Trên Windows: sử dụng win10toast (cài đặt riêng).
    """
    
    def __init__(self):
        self.enabled = True
        self.queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False

    async def start(self):
        """Khởi động loop xử lý thông báo."""
        self.is_running = True
        logger.info("Notification system started.")
        while self.is_running:
            try:
                notif = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._send_notification(notif)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing notification: {e}")

    def stop(self):
        """Dừng hệ thống thông báo."""
        self.is_running = False
        logger.info("Notification system stopped.")

    async def send(self, title: str, message: str, urgency: str = 'normal', icon: Optional[str] = None, timeout: int = 5000):
        """Gửi một thông báo mới vào hàng đợi."""
        if not self.enabled:
            return
            
        notif = Notification(
            title=title,
            message=message,
            urgency=urgency,
            icon=icon,
            timeout=timeout
        )
        await self.queue.put(notif)
        logger.debug(f"Notification queued: {title}")

    async def _send_notification(self, notif: Notification):
        """Thực thi gửi thông báo tới OS."""
        try:
            if os.name == 'posix':  # Linux/macOS
                await self._send_linux(notif)
            elif os.name == 'nt':  # Windows
                await self._send_windows(notif)
            else:
                logger.warning(f"Unsupported OS for notifications: {os.name}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def _send_linux(self, notif: Notification):
        """Gửi thông báo trên Linux bằng notify-send."""
        cmd = ["notify-send"]
        
        # Thêm urgency
        cmd.extend(["-u", notif.urgency])
        
        # Thêm timeout
        cmd.extend(["-t", str(notif.timeout)])
        
        # Thêm icon nếu có
        if notif.icon:
            cmd.extend(["-i", notif.icon])
            
        # Thêm title và message
        cmd.extend([notif.title, notif.message])
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.warning(f"notify-send failed: {stderr.decode()}")
        else:
            logger.info(f"Notification sent: {notif.title}")

    async def _send_windows(self, notif: Notification):
        """Gửi thông báo trên Windows (cần thư viện win10toast)."""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            
            # Chuyển đổi urgency sang thời gian hiển thị
            duration = notif.timeout / 1000.0
            
            # Thực hiện trong thread executor vì win10toast không async
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: toaster.show_toast(
                    title=notif.title,
                    msg=notif.message,
                    duration=duration,
                    threaded=True
                )
            )
            logger.info(f"Windows notification sent: {notif.title}")
        except ImportError:
            logger.warning("win10toast not installed. Install with: pip install win10toast")
        except Exception as e:
            logger.error(f"Windows notification error: {e}")

    async def send_welcome_back(self):
        """Thông báo khi user quay lại sau thời gian idle."""
        await self.send(
            title="Miku is here! 🌸",
            message="I missed you! Welcome back.",
            urgency='normal',
            timeout=3000
        )

    async def send_low_battery_warning(self):
        """Cảnh báo pin yếu (nếu tích hợp được với system monitor)."""
        await self.send(
            title="⚠️ Low Battery",
            message="Your battery is running low. You might want to plug in!",
            urgency='critical',
            timeout=10000
        )

    async def send_task_complete(self, task_name: str):
        """Thông báo hoàn thành tác vụ."""
        await self.send(
            title="✅ Task Complete",
            message=f"{task_name} has been completed.",
            urgency='low',
            timeout=3000
        )

notification_system_instance = NotificationSystem()
