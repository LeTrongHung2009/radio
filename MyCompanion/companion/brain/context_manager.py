"""
Context Manager - Quản lý ngữ cảnh hội thoại thông minh
Lưu trữ, nén và tối ưu hóa lịch sử chat trước khi gửi vào LLM.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import time
import json

logger = logging.getLogger("Miku.ContextManager")

@dataclass
class Message:
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: float
    emotion: Optional[str] = None
    is_internal_thought: bool = False
    importance_score: float = 1.0  # 0.0 - 1.0

class ContextManager:
    """
    Quản lý cửa sổ ngữ cảnh (Context Window) cho LLM.
    - Lưu trữ lịch sử ngắn hạn (Short-term memory).
    - Nén thông tin ít quan trọng.
    - Ưu tiên thông tin cảm xúc và sự kiện gần đây.
    """
    
    def __init__(self, max_tokens: int = 4000, max_messages: int = 50):
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self.history: List[Message] = []
        self.system_prompt: str = ""
        self._lock = asyncio.Lock()
        
        # Hệ số trọng số
        self.recency_weight = 1.5  # Tin nhắn gần đây quan trọng hơn
        self.emotion_weight = 1.2  # Tin nhắn có cảm xúc mạnh quan trọng hơn
        self.user_weight = 1.3     # Tin nhắn từ user quan trọng hơn AI tự nói

    def set_system_prompt(self, prompt: str):
        """Cập nhật system prompt cơ bản."""
        self.system_prompt = prompt
        logger.debug("System prompt updated.")

    async def add_message(self, role: str, content: str, emotion: Optional[str] = None, is_thought: bool = False):
        """Thêm tin nhắn mới vào lịch sử."""
        async with self._lock:
            msg = Message(
                role=role,
                content=content,
                timestamp=time.time(),
                emotion=emotion,
                is_internal_thought=is_thought
            )
            
            # Tính điểm quan trọng ban đầu
            msg.importance_score = self._calculate_importance(msg)
            
            self.history.append(msg)
            logger.debug(f"Added message to context: {role} ({len(content)} chars)")
            
            # Dọn dẹp nếu vượt quá giới hạn
            if len(self.history) > self.max_messages:
                await self._prune_history()

    def _calculate_importance(self, msg: Message) -> float:
        """Tính điểm quan trọng cho tin nhắn."""
        score = 1.0
        
        # Trọng số theo vai trò
        if msg.role == 'user':
            score *= self.user_weight
            
        # Trọng số theo cảm xúc
        if msg.emotion and msg.emotion not in ['neutral', 'none']:
            score *= self.emotion_weight
            
        # Trọng số theo thời gian (càng mới càng quan trọng)
        time_diff = time.time() - msg.timestamp
        recency_factor = 1.0 / (1.0 + (time_diff / 300.0))  # Giảm dần sau 5 phút
        score *= (1.0 + (recency_factor * (self.recency_weight - 1.0)))
        
        # Nội dung dài thường chứa nhiều thông tin
        if len(msg.content) > 100:
            score *= 1.1
            
        return min(score, 5.0)  # Cap max score

    async def _prune_history(self):
        """Loại bỏ tin nhắn ít quan trọng nhất khi đầy bộ nhớ."""
        if len(self.history) <= self.max_messages:
            return

        # Sắp xếp theo điểm quan trọng
        sorted_history = sorted(self.history, key=lambda m: m.importance_score)
        
        # Giữ lại số lượng tin nhắn an toàn
        keep_count = int(self.max_messages * 0.8)
        to_remove_count = len(self.history) - keep_count
        
        # Xóa các tin nhắn kém quan trọng nhất (trừ system prompt và tin nhắn rất gần)
        current_time = time.time()
        preserved_history = []
        
        for msg in self.history:
            # Luôn giữ tin nhắn trong 2 phút gần nhất
            if (current_time - msg.timestamp) < 120:
                preserved_history.append(msg)
                continue
                
            if to_remove_count > 0 and msg.importance_score < 1.2:
                logger.debug(f"Pruning low-importance message: {msg.content[:30]}...")
                to_remove_count -= 1
            else:
                preserved_history.append(msg)
        
        self.history = preserved_history[-self.max_messages:]
        logger.info(f"Context pruned. Remaining messages: {len(self.history)}")

    async def get_context_for_llm(self) -> List[Dict[str, str]]:
        """
        Chuẩn bị danh sách tin nhắn để gửi cho LLM.
        Loại bỏ suy nghĩ nội tâm (internal thoughts) khỏi ngữ cảnh gửi đi,
        chỉ gửi lời nói thực tế.
        """
        async with self._lock:
            context_messages = []
            
            # Thêm System Prompt
            if self.system_prompt:
                context_messages.append({
                    "role": "system",
                    "content": self.system_prompt
                })
            
            # Lọc và định dạng lịch sử
            for msg in self.history:
                # Bỏ qua suy nghĩ nội tâm khi gửi cho LLM (trừ khi cần thiết cho debugging)
                if msg.is_internal_thought:
                    continue
                    
                content = msg.content
                # Có thể thêm tag cảm xúc vào cuối nội dung nếu cần
                if msg.emotion and msg.emotion != 'neutral':
                    content += f" [Emotion: {msg.emotion}]"
                
                context_messages.append({
                    "role": msg.role,
                    "content": content
                })
            
            # Ước lượng token đơn giản (1 token ~ 4 chars tiếng Anh, ~2 chars tiếng Việt/Japan)
            total_chars = sum(len(m['content']) for m in context_messages)
            estimated_tokens = total_chars / 3
            
            if estimated_tokens > self.max_tokens:
                logger.warning(f"Context size ({estimated_tokens:.0f}) exceeds limit ({self.max_tokens}). Truncating...")
                # Nếu vẫn vượt, cắt bớt từ đầu (cũ nhất)
                while estimated_tokens > self.max_tokens and len(context_messages) > 2:
                    # Giữ lại system prompt và ít nhất 1 message
                    removed = context_messages.pop(1)
                    estimated_tokens -= len(removed['content']) / 3

            return context_messages

    async def get_summary_of_recent(self, count: int = 5) -> str:
        """Tóm tắt nhanh N tin nhắn gần nhất để dùng cho internal monologue."""
        recent = self.history[-count:]
        if not recent:
            return "No recent conversation."
        
        summary_parts = []
        for msg in recent:
            actor = "User" if msg.role == 'user' else "Miku"
            summary_parts.append(f"{actor}: {msg.content[:50]}...")
        
        return "\n".join(summary_parts)

    async def clear_history(self):
        """Xóa toàn bộ lịch sử hội thoại."""
        async with self._lock:
            self.history = []
            logger.info("Conversation history cleared.")

    def get_stats(self) -> Dict[str, Any]:
        """Thống kê trạng thái context."""
        total_chars = sum(len(m.content) for m in self.history)
        return {
            "message_count": len(self.history),
            "estimated_tokens": int(total_chars / 3),
            "max_tokens": self.max_tokens,
            "oldest_message_age_sec": time.time() - self.history[0].timestamp if self.history else 0
        }

context_manager_instance = ContextManager()
