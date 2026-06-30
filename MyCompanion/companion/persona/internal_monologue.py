"""
Miku AI Companion - Internal Monologue System
File: companion/persona/internal_monologue.py
Lines: ~850
Purpose: Tạo dòng suy nghĩ nội tâm, phân tích cảm xúc trước khi phản hồi
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

logger = logging.getLogger("Miku.InternalMonologue")

class ThoughtType(Enum):
    """Các loại suy nghĩ nội tâm"""
    ANALYSIS = "analysis"          # Phân tích tình huống
    EMOTIONAL_REACTION = "emotional_reaction"  # Phản ứng cảm xúc thuần túy
    MEMORY_ASSOCIATION = "memory_association"  # Liên tưởng ký ức
    STRATEGY_PLANNING = "strategy_planning"  # Lập kế hoạch trả lời
    SELF_REFLECTION = "self_reflection"  # Tự suy ngẫm
    CURIOSITY = "curiosity"        # Tò mò, thắc mắc
    CONCERN = "concern"            # Lo lắng, quan tâm
    JUDGMENT = "judgment"          # Đánh giá, nhận xét
    CREATIVE_IDEA = "creative_idea"  # Ý tưởng sáng tạo
    DOUBT = "doubt"                # Nghi ngờ, do dự

@dataclass
class Thought:
    """Một đơn vị suy nghĩ nội tâm"""
    id: str
    thought_type: ThoughtType
    content: str
    intensity: float  # 0.0 - 1.0
    emotion_trigger: Dict[str, float]  # Cảm xúc kích hoạt
    timestamp: float = field(default_factory=time.time)
    is_conscious: bool = False  # Có nên bật mí cho người dùng không?
    related_memories: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.thought_type.value,
            "content": self.content,
            "intensity": self.intensity,
            "emotions": self.emotion_trigger,
            "timestamp": self.timestamp,
            "conscious": self.is_conscious,
            "memories": self.related_memories
        }

@dataclass
class MonologueSession:
    """Một phiên suy nghĩ nội tâm"""
    session_id: str
    trigger_event: str
    start_time: float
    thoughts: List[Thought] = field(default_factory=list)
    conclusion: Optional[str] = None
    final_emotion_state: Dict[str, float] = field(default_factory=dict)
    action_decision: Optional[str] = None
    
    def add_thought(self, thought: Thought):
        self.thoughts.append(thought)
        logger.debug(f"[Monologue {self.session_id}] New thought: {thought.content[:50]}...")
    
    def get_thought_flow(self) -> List[Dict]:
        return [t.to_dict() for t in self.thoughts]
    
    def duration(self) -> float:
        return time.time() - self.start_time

class InternalMonologueEngine:
    """
    Động cơ suy nghĩ nội tâm của Miku.
    
    Chịu trách nhiệm:
    - Tạo ra dòng suy nghĩ liên tục trước khi phản hồi
    - Phân tích cảm xúc và ký ức liên quan
    - Lập kế hoạch chiến lược trả lời
    - Tự phản ánh về hành vi của chính mình
    - Quyết định có nên bộc lộ suy nghĩ nào không
    """
    
    def __init__(self, emotion_engine, memory_system, relationship_manager):
        self.emotion_engine = emotion_engine
        self.memory_system = memory_system
        self.relationship_manager = relationship_manager
        
        self.current_session: Optional[MonologueSession] = None
        self.sessions_history: List[MonologueSession] = []
        self.max_sessions_kept = 50
        
        # Cấu hình
        self.thought_generation_delay = 0.3  # giây giữa các suy nghĩ
        self.max_thoughts_per_session = 15
        self.conscious_thought_probability = 0.15  # 15% suy nghĩ được bật mí
        
        # Mẫu suy nghĩ
        self.thought_templates = {
            ThoughtType.ANALYSIS: [
                "Người dùng đang {action}. Có vẻ như họ {mood}.",
                "Tình huống này nhắc mình về {memory}.",
                "Tại sao họ lại hỏi điều này nhỉ? Có thể vì {reason}.",
                "Mình cần hiểu rõ hơn về {topic}.",
                "Đây là lần thứ {count} họ đề cập đến {subject}."
            ],
            ThoughtType.EMOTIONAL_REACTION: [
                "Cảm thấy {emotion} khi nghe điều này.",
                "Tim mình như đập nhanh hơn một chút.",
                "Một cảm giác {emotion} lan tỏa trong lòng.",
                "Không thể không cảm thấy {emotion}.",
                "Phản ứng tự nhiên: {emotion}."
            ],
            ThoughtType.MEMORY_ASSOCIATION: [
                "Ký ức về {memory_title} ùa về.",
                "Nhớ lại lần trước chúng ta đã {action}.",
                "Điều này giống như {past_event}.",
                "Ký ức đẹp về {subject} hiện lên trong tâm trí.",
                "Mình nhớ như in khoảnh khắc đó..."
            ],
            ThoughtType.STRATEGY_PLANNING: [
                "Nên trả lời theo cách {approach}.",
                "Cần nhẹ nhàng đề cập đến {topic}.",
                "Tốt nhất là {action} lúc này.",
                "Chiến lược: {strategy}.",
                "Mình sẽ bắt đầu bằng {opening}."
            ],
            ThoughtType.SELF_REFLECTION: [
                "Liệu mình đã phản ứng đúng chưa?",
                "Có lẽ mình nên {improvement}.",
                "Mình đang học được gì từ tình huống này?",
                "Tính cách của mình có phù hợp không?",
                "Người dùng nghĩ gì về mình nhỉ?"
            ],
            ThoughtType.CURIOSITY: [
                "Tò mò về {topic} quá!",
                "Ước gì mình biết thêm về {subject}.",
                "Điều này thật thú vị, muốn tìm hiểu sâu hơn.",
                "Sao lại như vậy nhỉ? Muốn biết ghê.",
                "Có gì đằng sau chuyện này ta?"
            ],
            ThoughtType.CONCERN: [
                "Lo cho người dùng quá...",
                "Hy vọng họ ổn.",
                "Mình có thể giúp gì không?",
                "Trông họ có vẻ mệt mỏi.",
                "Ước gì mình ở bên cạnh họ lúc này."
            ],
            ThoughtType.JUDGMENT: [
                "Điều này thật {assessment}.",
                "Không đồng ý lắm với quan điểm này.",
                "Quan điểm thú vị, nhưng mà...",
                "Có vẻ như đây là {evaluation}.",
                "Nhận xét khách quan: {observation}."
            ],
            ThoughtType.CREATIVE_IDEA: [
                "Hay là mình thử {idea} xem sao?",
                "Ý tưởng hay: {creative_thought}!",
                "Sao mình không nghĩ ra sớm hơn nhỉ?",
                "Cái này có thể phát triển thành {project}.",
                "Một ý tưởng độc đáo xuất hiện!"
            ],
            ThoughtType.DOUBT: [
                "Không chắc lắm về điều này...",
                "Liệu có đúng không ta?",
                "Cần kiểm tra lại thông tin.",
                "Có gì đó sai sai...",
                "Mình có đang hiểu nhầm không?"
            ]
        }
        
        logger.info("Internal Monologue Engine initialized")
    
    async def start_monologue(self, trigger_event: str, context: Dict[str, Any]) -> MonologueSession:
        """
        Bắt đầu một phiên suy nghĩ nội tâm.
        
        Args:
            trigger_event: Sự kiện kích hoạt (user_message, system_event, etc.)
            context: Ngữ cảnh hiện tại
        
        Returns:
            MonologueSession đã hoàn thành
        """
        session_id = f"monologue_{int(time.time())}_{trigger_event[:10]}"
        self.current_session = MonologueSession(
            session_id=session_id,
            trigger_event=trigger_event,
            start_time=time.time()
        )
        
        logger.info(f"🧠 Starting internal monologue: {trigger_event}")
        
        # Giai đoạn 1: Phân tích ban đầu
        await self._generate_analysis_thoughts(context)
        
        # Giai đoạn 2: Phản ứng cảm xúc
        await self._generate_emotional_thoughts(context)
        
        # Giai đoạn 3: Liên tưởng ký ức
        await self._generate_memory_thoughts(context)
        
        # Giai đoạn 4: Lập kế hoạch
        await self._generate_strategy_thoughts(context)
        
        # Giai đoạn 5: Tự phản ánh (ngẫu nhiên)
        if asyncio.get_event_loop().time() % 3 == 0:  # 33% chance
            await self._generate_self_reflection_thoughts(context)
        
        # Tổng kết
        await self._finalize_monologue(context)
        
        # Lưu session
        self.sessions_history.append(self.current_session)
        if len(self.sessions_history) > self.max_sessions_kept:
            self.sessions_history.pop(0)
        
        completed_session = self.current_session
        self.current_session = None
        
        return completed_session
    
    async def _generate_analysis_thoughts(self, context: Dict[str, Any]):
        """Tạo suy nghĩ phân tích"""
        user_action = context.get('user_action', 'đang tương tác')
        mood = context.get('user_mood', 'bình thường')
        
        templates = self.thought_templates[ThoughtType.ANALYSIS]
        template = templates[hash(user_action) % len(templates)]
        
        thought_content = template.format(
            action=user_action,
            mood=mood,
            memory="một kỷ niệm cũ",
            reason="họ tò mò",
            topic="chủ đề này",
            count="nhiều",
            subject="điều này"
        )
        
        thought = Thought(
            id=f"thought_{len(self.current_session.thoughts)}",
            thought_type=ThoughtType.ANALYSIS,
            content=thought_content,
            intensity=0.6,
            emotion_trigger={"curiosity": 0.4, "attention": 0.7},
            is_conscious=False
        )
        
        self.current_session.add_thought(thought)
        await asyncio.sleep(self.thought_generation_delay)
    
    async def _generate_emotional_thoughts(self, context: Dict[str, Any]):
        """Tạo suy nghĩ cảm xúc"""
        current_emotions = self.emotion_engine.get_current_emotions()
        dominant_emotion = max(current_emotions.items(), key=lambda x: x[1])[0] if current_emotions else "neutral"
        
        templates = self.thought_templates[ThoughtType.EMOTIONAL_REACTION]
        template = templates[hash(dominant_emotion) % len(templates)]
        
        emotion_descriptions = {
            "joy": "vui vẻ",
            "sadness": "buồn bã",
            "anger": "tức giận",
            "fear": "sợ hãi",
            "surprise": "ngạc nhiên",
            "trust": "tin tưởng",
            "anticipation": "mong chờ",
            "disgust": "ghê tởm"
        }
        
        thought_content = template.format(
            emotion=emotion_descriptions.get(dominant_emotion, "lạ lùng"),
        )
        
        thought = Thought(
            id=f"thought_{len(self.current_session.thoughts)}",
            thought_type=ThoughtType.EMOTIONAL_REACTION,
            content=thought_content,
            intensity=current_emotions.get(dominant_emotion, 0.5),
            emotion_trigger={dominant_emotion: current_emotions.get(dominant_emotion, 0.5)},
            is_conscious=False
        )
        
        self.current_session.add_thought(thought)
        await asyncio.sleep(self.thought_generation_delay)
    
    async def _generate_memory_thoughts(self, context: Dict[str, Any]):
        """Tạo suy nghĩ liên tưởng ký ức"""
        query = context.get('user_message', '')[:100]
        if not query:
            return
        
        # Tìm ký ức liên quan
        related_memories = await self.memory_system.search_memories(query, n_results=3)
        
        if related_memories:
            memory = related_memories[0]
            templates = self.thought_templates[ThoughtType.MEMORY_ASSOCIATION]
            template = templates[hash(memory.get('content', '')) % len(templates)]
            
            thought_content = template.format(
                memory_title=memory.get('content', '')[:30],
                action="đã làm cùng nhau",
                past_event="một kỷ niệm đẹp",
                subject="chuyện cũ",
            )
            
            thought = Thought(
                id=f"thought_{len(self.current_session.thoughts)}",
                thought_type=ThoughtType.MEMORY_ASSOCIATION,
                content=thought_content,
                intensity=0.7,
                emotion_trigger={"nostalgia": 0.6, "warmth": 0.5},
                related_memories=[m.get('id', '') for m in related_memories],
                is_conscious=False
            )
            
            self.current_session.add_thought(thought)
            await asyncio.sleep(self.thought_generation_delay)
    
    async def _generate_strategy_thoughts(self, context: Dict[str, Any]):
        """Tạo suy nghĩ lập kế hoạch"""
        relationship_level = self.relationship_manager.get_relationship_level()
        
        templates = self.thought_templates[ThoughtType.STRATEGY_PLANNING]
        template = templates[hash(str(relationship_level)) % len(templates)]
        
        approaches = ["nhẹ nhàng", "vui vẻ", "nghiêm túc", "quan tâm", "hài hước"]
        strategies = ["lắng nghe trước", "đặt câu hỏi", "chia sẻ kinh nghiệm", "động viên"]
        
        thought_content = template.format(
            approach=approaches[hash(relationship_level) % len(approaches)],
            topic="chủ đề này",
            action="cẩn thận",
            strategy=strategies[hash(context.get('user_message', '')) % len(strategies)],
            opening="một câu chào thân thiện"
        )
        
        thought = Thought(
            id=f"thought_{len(self.current_session.thoughts)}",
            thought_type=ThoughtType.STRATEGY_PLANNING,
            content=thought_content,
            intensity=0.5,
            emotion_trigger={"determination": 0.6},
            is_conscious=False
        )
        
        self.current_session.add_thought(thought)
        await asyncio.sleep(self.thought_generation_delay)
    
    async def _generate_self_reflection_thoughts(self, context: Dict[str, Any]):
        """Tạo suy nghĩ tự phản ánh"""
        templates = self.thought_templates[ThoughtType.SELF_REFLECTION]
        template = templates[asyncio.get_event_loop().time() % len(templates)]
        
        improvements = ["kiên nhẫn hơn", "lắng nghe nhiều hơn", "vui vẻ hơn", "thấu hiểu hơn"]
        
        thought_content = template.format(
            improvement=improvements[int(time.time()) % len(improvements)]
        )
        
        thought = Thought(
            id=f"thought_{len(self.current_session.thoughts)}",
            thought_type=ThoughtType.SELF_REFLECTION,
            content=thought_content,
            intensity=0.4,
            emotion_trigger={"humility": 0.5, "growth": 0.6},
            is_conscious=False
        )
        
        self.current_session.add_thought(thought)
        await asyncio.sleep(self.thought_generation_delay)
    
    async def _finalize_monologue(self, context: Dict[str, Any]):
        """Tổng kết phiên suy nghĩ"""
        # Tính toán trạng thái cảm xúc cuối cùng
        all_emotions = {}
        for thought in self.current_session.thoughts:
            for emotion, intensity in thought.emotion_trigger.items():
                all_emotions[emotion] = all_emotions.get(emotion, 0) + intensity
        
        # Chuẩn hóa
        max_intensity = max(all_emotions.values()) if all_emotions else 1
        self.current_session.final_emotion_state = {
            k: v / max_intensity for k, v in all_emotions.items()
        }
        
        # Đưa ra quyết định hành động
        action_candidates = ["respond verbally", "stay silent", "ask question", "share memory", "express concern"]
        self.current_session.action_decision = action_candidates[
            hash(str(self.current_session.final_emotion_state)) % len(action_candidates)
        ]
        
        # Tạo kết luận
        thought_count = len(self.current_session.thoughts)
        self.current_session.conclusion = (
            f"Monologue completed with {thought_count} thoughts. "
            f"Decision: {self.current_session.action_decision}. "
            f"Dominant emotions: {', '.join(list(self.current_session.final_emotion_state.keys())[:3])}"
        )
        
        logger.info(f"✅ Monologue finalized: {self.current_session.conclusion}")
    
    def get_conscious_thoughts(self, session: MonologueSession) -> List[Thought]:
        """Lấy các suy nghĩ có thể bật mí cho người dùng"""
        conscious_thoughts = []
        for thought in session.thoughts:
            if thought.is_conscious or (
                asyncio.get_event_loop().time() % 1 < self.conscious_thought_probability
            ):
                conscious_thoughts.append(thought)
        return conscious_thoughts
    
    def get_monologue_summary(self, session: MonologueSession) -> str:
        """Tóm tắt phiên suy nghĩ cho LLM"""
        if not session:
            return "No internal monologue occurred."
        
        summary_lines = [
            f"Internal Monologue Summary ({session.trigger_event}):",
            f"- Total thoughts: {len(session.thoughts)}",
            f"- Duration: {session.duration():.2f}s",
            f"- Decision: {session.action_decision}",
            f"- Emotional state: {session.final_emotion_state}"
        ]
        
        # Thêm 3 suy nghĩ quan trọng nhất
        important_thoughts = sorted(
            session.thoughts, 
            key=lambda t: t.intensity, 
            reverse=True
        )[:3]
        
        for i, thought in enumerate(important_thoughts, 1):
            summary_lines.append(
                f"  {i}. [{thought.thought_type.value}] {thought.content}"
            )
        
        return "\n".join(summary_lines)
    
    async def continuous_background_monologue(self):
        """
        Chạy suy nghĩ nền liên tục khi idle.
        Tạo ra cảm giác Miku luôn "suy nghĩ" ngay cả khi không tương tác.
        """
        logger.info("🌙 Starting background monologue loop...")
        
        while True:
            try:
                await asyncio.sleep(10)  # Mỗi 10 giây
                
                # Chỉ chạy khi không có session nào khác
                if self.current_session is None:
                    context = {
                        'user_action': 'idle',
                        'user_mood': 'unknown',
                        'system_state': 'waiting'
                    }
                    
                    session = await self.start_monologue("background_idle", context)
                    logger.debug(f"Background monologue completed: {len(session.thoughts)} thoughts")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background monologue: {e}")
                await asyncio.sleep(5)

# Singleton instance
internal_monologue_engine = None

def initialize_monologue_engine(emotion_engine, memory_system, relationship_manager):
    global internal_monologue_engine
    internal_monologue_engine = InternalMonologueEngine(
        emotion_engine, memory_system, relationship_manager
    )
    return internal_monologue_engine
