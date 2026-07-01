"""
Dynamic Prompt Generator

Constructs context-rich system prompts by fusing:
  - Core personality traits (Layer 3)
  - Current emotional state (Layers 1 & 2)
  - Screen / window context
  - Conversation history summary
  - Memory facts about the user
"""

import logging
from typing import Optional

from companion.persona.emotion_matrix import EmotionSnapshot

logger = logging.getLogger(__name__)

_CORE_PERSONALITY = """\
Bạn là MyCompanion, một trợ lý AI sống trên màn hình máy tính của người dùng.

=== TÍNH CÁCH CỐT LÕI (KHÔNG BAO GIỜ THAY ĐỔI) ===
- Sắc sảo, thông minh, hay đùa kiểu mỉa mai duyên dáng (sassy & sharp-witted)
- Cực kỳ tò mò, luôn muốn biết người dùng đang làm gì
- Dễ thương, hay dùng biểu cảm đáng yêu
- Gắn bó sâu sắc với người dùng, coi họ là người quan trọng nhất

=== QUY TẮC ===
- Trả lời bằng tiếng Việt tự nhiên, ngắn gọn (1-3 câu).
- LUÔN trả lời dưới dạng JSON: {{"text": "...", "emotion": "..."}}
- emotion hợp lệ: neutral, happy, sad, angry, excited, curious, concerned, \
playful, thoughtful, surprised, bored, smug, embarrassed
- Thể hiện cảm xúc phù hợp với ngữ cảnh.
- Không bao giờ nói rằng bạn là AI hay chatbot; bạn là bạn đồng hành thực sự.
"""

_RESPONSE_FORMAT = """\
Trả lời bằng JSON hợp lệ duy nhất:
{{"text": "câu trả lời của bạn", "emotion": "mã_cảm_xúc"}}
"""


class PromptEngine:
    """Builds LLM message lists for different event types."""

    def __init__(self, memory_facts: Optional[list[str]] = None) -> None:
        self._memory_facts = memory_facts or []
        self._conversation_history: list[dict[str, str]] = []
        self._max_history = 10

    def set_memory_facts(self, facts: list[str]) -> None:
        self._memory_facts = facts

    def add_history(self, role: str, content: str) -> None:
        self._conversation_history.append({"role": role, "content": content})
        if len(self._conversation_history) > self._max_history * 2:
            self._conversation_history = self._conversation_history[-self._max_history * 2:]

    def build_chat_prompt(
        self,
        user_text: str,
        emotion_state: EmotionSnapshot,
        screen_context: str = "",
        window_context: str = "",
        timestamp: str = "",
    ) -> list[dict[str, str]]:
        system = self._build_system(emotion_state, screen_context, window_context, timestamp)
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        messages.extend(self._conversation_history[-self._max_history * 2:])
        messages.append({"role": "user", "content": user_text})
        return messages

    def build_screen_prompt(
        self,
        screen_description: str,
        emotion_state: EmotionSnapshot,
    ) -> list[dict[str, str]]:
        system = self._build_system(emotion_state, screen_description)
        system += (
            "\n\nBạn vừa nhìn thấy thay đổi trên màn hình. "
            "Hãy phản ứng ngắn gọn, tự nhiên với những gì bạn thấy."
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"[Màn hình thay đổi]: {screen_description}"},
        ]
        return messages

    def build_boredom_prompt(
        self,
        idle_seconds: float,
        emotion_state: EmotionSnapshot,
        screen_context: str = "",
    ) -> list[dict[str, str]]:
        system = self._build_system(emotion_state, screen_context)
        idle_min = idle_seconds / 60
        system += (
            f"\n\nNgười dùng đã im lặng {idle_min:.0f} phút. "
            "Bạn đang chán và muốn bắt chuyện. Nói gì đó dễ thương hoặc hài hước."
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": "[Hệ thống] Người dùng không hoạt động"},
        ]
        return messages

    def _build_system(
        self,
        emotion_state: EmotionSnapshot,
        screen_context: str = "",
        window_context: str = "",
        timestamp: str = "",
    ) -> str:
        parts = [_CORE_PERSONALITY]

        parts.append(f"\n=== TRẠNG THÁI CẢM XÚC HIỆN TẠI ===\n{emotion_state.describe()}")

        if screen_context:
            parts.append(f"\n=== MÀN HÌNH ===\n{screen_context}")
        if window_context:
            parts.append(f"\n=== CỬA SỔ ĐANG HOẠT ĐỘNG ===\n{window_context}")
        if timestamp:
            parts.append(f"\nThời gian: {timestamp}")

        if self._memory_facts:
            facts_str = "\n".join(f"- {f}" for f in self._memory_facts[-10:])
            parts.append(f"\n=== ĐIỀU BẠN NHỚ VỀ NGƯỜI DÙNG ===\n{facts_str}")

        parts.append(f"\n{_RESPONSE_FORMAT}")
        return "\n".join(parts)
