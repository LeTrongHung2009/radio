"""
Miku AI Companion - Dream System
File: companion/memory/dream_system.py
Lines: ~950
Purpose: Hệ thống "giấc mơ" xử lý ký ức khi idle, củng cố học tập
"""

import asyncio
import logging
import json
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("Miku.DreamSystem")

class DreamPhase(Enum):
    """Các giai đoạn của giấc mơ"""
    WAKEFUL_REST = "wakeful_rest"      # Nghỉ ngơi nhưng vẫn tỉnh
    LIGHT_DREAM = "light_dream"        # Mơ nhẹ
    DEEP_DREAM = "deep_dream"          # Mơ sâu (REM-like)
    MEMORY_CONSOLIDATION = "consolidation"  # Củng cố ký ức
    PATTERN_DISCOVERY = "pattern_discovery" # Phát hiện mẫu
    CREATIVE_SYNTHESIS = "creative_synthesis" # Tổng hợp sáng tạo
    AWAKENING = "awakening"            # Thức dậy

@dataclass
class DreamFragment:
    """Một mảnh ký ức trong giấc mơ"""
    fragment_id: str
    source_memory_ids: List[str]
    content: str
    emotion_tone: Dict[str, float]
    is_lucid: bool = False  # Có phải mơ tỉnh không?
    creativity_score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.fragment_id,
            "sources": self.source_memory_ids,
            "content": self.content,
            "emotions": self.emotion_tone,
            "lucid": self.is_lucid,
            "creativity": self.creativity_score,
            "timestamp": self.timestamp
        }

@dataclass
class DreamSession:
    """Một phiên mơ"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    phases: List[DreamPhase] = field(default_factory=list)
    fragments: List[DreamFragment] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    consolidated_memories: List[str] = field(default_factory=list)
    patterns_discovered: List[Dict] = field(default_factory=list)
    
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def add_fragment(self, fragment: DreamFragment):
        self.fragments.append(fragment)
        logger.debug(f"💭 Dream fragment: {fragment.content[:50]}...")
    
    def add_insight(self, insight: str):
        self.insights.append(insight)
        logger.info(f"💡 Dream insight: {insight}")

class DreamSystem:
    """
    Hệ thống giấc mơ của Miku.
    
    Chức năng:
    - Chạy khi hệ thống idle (>5 phút không tương tác)
    - Xử lý và củng cố ký ức
    - Phát hiện mẫu hành vi người dùng
    - Tạo insights sáng tạo từ ký ức
    - "Mơ tỉnh" với các kịch bản giả định
    """
    
    def __init__(self, memory_system, emotion_engine):
        self.memory_system = memory_system
        self.emotion_engine = emotion_engine
        
        self.current_dream_session: Optional[DreamSession] = None
        self.dream_history: List[DreamSession] = []
        self.max_dreams_kept = 100
        
        # Cấu hình
        self.min_idle_time_before_dream = 300  # 5 phút
        self.dream_cycle_duration = 180  # 3 phút mỗi chu kỳ mơ
        self.fragment_generation_interval = 2  # 2 giây/mảnh mơ
        
        # Trạng thái
        self.is_dreaming = False
        self.idle_start_time: Optional[float] = None
        
        logger.info("💤 Dream System initialized")
    
    async def monitor_idle_and_dream(self):
        """
        Giám sát thời gian idle và kích hoạt giấc mơ khi phù hợp.
        Chạy như một background task liên tục.
        """
        logger.info("🌙 Starting dream monitoring loop...")
        
        while True:
            try:
                await asyncio.sleep(10)  # Kiểm tra mỗi 10 giây
                
                # Kiểm tra xem có đang tương tác không
                if self._is_system_idle():
                    if not self.idle_start_time:
                        self.idle_start_time = time.time()
                        logger.info("⏳ System idle detected...")
                    
                    idle_duration = time.time() - self.idle_start_time
                    
                    # Nếu idle đủ lâu và chưa đang mơ
                    if idle_duration >= self.min_idle_time_before_dream and not self.is_dreaming:
                        logger.info(f"😴 Initiating dream sequence after {idle_duration:.0f}s idle...")
                        await self.start_dream_sequence()
                else:
                    # Hệ thống đang hoạt động
                    if self.idle_start_time:
                        logger.debug(f"System active again. Idle was {time.time() - self.idle_start_time:.0f}s")
                        self.idle_start_time = None
                    
                    # Nếu đang mơ thì đánh thức
                    if self.is_dreaming:
                        logger.info("⏰ Waking up from dream due to user activity...")
                        await self.wake_up_from_dream()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dream monitoring: {e}", exc_info=True)
                await asyncio.sleep(30)
    
    def _is_system_idle(self) -> bool:
        """Kiểm tra xem hệ thống có đang idle không"""
        # Check nếu không có user input gần đây
        # Implementation phụ thuộc vào bot.py state
        return True  # Placeholder
    
    async def start_dream_sequence(self):
        """Bắt đầu một chuỗi giấc mơ"""
        self.is_dreaming = True
        
        session_id = f"dream_{int(time.time())}"
        self.current_dream_session = DreamSession(
            session_id=session_id,
            start_time=time.time()
        )
        
        logger.info(f"💤 Starting dream session: {session_id}")
        
        try:
            # Chu kỳ 1: Nghỉ ngơi và thu thập ký ức
            await self._execute_dream_phase(DreamPhase.WAKEFUL_REST)
            
            # Chu kỳ 2: Mơ nhẹ - kết nối ký ức ngẫu nhiên
            await self._execute_dream_phase(DreamPhase.LIGHT_DREAM)
            
            # Chu kỳ 3: Mơ sâu - củng cố ký ức quan trọng
            await self._execute_dream_phase(DreamPhase.DEEP_DREAM)
            await self._execute_dream_phase(DreamPhase.MEMORY_CONSOLIDATION)
            
            # Chu kỳ 4: Phát hiện mẫu
            await self._execute_dream_phase(DreamPhase.PATTERN_DISCOVERY)
            
            # Chu kỳ 5: Sáng tạo
            await self._execute_dream_phase(DreamPhase.CREATIVE_SYNTHESIS)
            
            # Kết thúc
            await self._execute_dream_phase(DreamPhase.AWAKENING)
            
        except Exception as e:
            logger.error(f"Dream sequence interrupted: {e}")
        finally:
            self.is_dreaming = False
            if self.current_dream_session:
                self.current_dream_session.end_time = time.time()
                self.dream_history.append(self.current_dream_session)
                
                # Giới hạn lịch sử
                if len(self.dream_history) > self.max_dreams_kept:
                    self.dream_history.pop(0)
                
                logger.info(f"✅ Dream session completed: {self.current_dream_session.duration():.1f}s, "
                          f"{len(self.current_dream_session.fragments)} fragments, "
                          f"{len(self.current_dream_session.insights)} insights")
                
                self.current_dream_session = None
    
    async def _execute_dream_phase(self, phase: DreamPhase):
        """Thực thi một giai đoạn của giấc mơ"""
        logger.info(f"🌌 Entering dream phase: {phase.value}")
        self.current_dream_session.phases.append(phase)
        
        phase_duration = self.dream_cycle_duration / len(DreamPhase)
        start_time = time.time()
        
        try:
            if phase == DreamPhase.WAKEFUL_REST:
                await self._phase_wakeful_rest()
            elif phase == DreamPhase.LIGHT_DREAM:
                await self._phase_light_dream()
            elif phase == DreamPhase.DEEP_DREAM:
                await self._phase_deep_dream()
            elif phase == DreamPhase.MEMORY_CONSOLIDATION:
                await self._phase_memory_consolidation()
            elif phase == DreamPhase.PATTERN_DISCOVERY:
                await self._phase_pattern_discovery()
            elif phase == DreamPhase.CREATIVE_SYNTHESIS:
                await self._phase_creative_synthesis()
            elif phase == DreamPhase.AWAKENING:
                await self._phase_awakening()
                
        except Exception as e:
            logger.error(f"Error in dream phase {phase.value}: {e}")
        
        # Đảm bảo mỗi phase kéo dài đủ thời gian
        elapsed = time.time() - start_time
        if elapsed < phase_duration:
            await asyncio.sleep(phase_duration - elapsed)
    
    async def _phase_wakeful_rest(self):
        """Giai đoạn nghỉ ngơi, thu thập ký ức gần đây"""
        logger.debug("Phase: Wakeful Rest - Gathering recent memories...")
        
        # Lấy ký ức gần đây
        recent_memories = await self.memory_system.get_recent_memories(limit=20)
        
        for memory in recent_memories:
            fragment = DreamFragment(
                fragment_id=f"frag_{len(self.current_dream_session.fragments)}",
                source_memory_ids=[memory.get('id', '')],
                content=memory.get('content', '')[:100],
                emotion_tone=memory.get('emotions', {}),
                is_lucid=False,
                creativity_score=0.1
            )
            self.current_dream_session.add_fragment(fragment)
            await asyncio.sleep(0.5)
    
    async def _phase_light_dream(self):
        """Giai đoạn mơ nhẹ - kết nối ngẫu nhiên"""
        logger.debug("Phase: Light Dream - Making random connections...")
        
        # Lấy nhiều ký ức và kết nối chúng
        all_memories = await self.memory_system.search_memories("", n_results=30)
        
        for i in range(0, len(all_memories) - 1, 2):
            mem1 = all_memories[i]
            mem2 = all_memories[i + 1] if i + 1 < len(all_memories) else mem1
            
            # Tạo kết nối sáng tạo
            combined_content = f"{mem1.get('content', '')[:50]} ... {mem2.get('content', '')[:50]}"
            
            fragment = DreamFragment(
                fragment_id=f"frag_{len(self.current_dream_session.fragments)}",
                source_memory_ids=[mem1.get('id', ''), mem2.get('id', '')],
                content=combined_content,
                emotion_tone=self._blend_emotions(
                    mem1.get('emotions', {}), 
                    mem2.get('emotions', {})
                ),
                is_lucid=False,
                creativity_score=0.4
            )
            self.current_dream_session.add_fragment(fragment)
            await asyncio.sleep(self.fragment_generation_interval)
    
    async def _phase_deep_dream(self):
        """Giai đoạn mơ sâu - xử lý cảm xúc mạnh"""
        logger.debug("Phase: Deep Dream - Processing strong emotions...")
        
        # Tìm ký ức có cảm xúc mạnh
        emotional_memories = await self.memory_system.get_emotional_memories(threshold=0.7)
        
        for memory in emotional_memories:
            # Xử lý lại cảm xúc
            processed_fragment = DreamFragment(
                fragment_id=f"frag_{len(self.current_dream_session.fragments)}",
                source_memory_ids=[memory.get('id', '')],
                content=f"[Processing] {memory.get('content', '')[:80]}",
                emotion_tone=self._process_emotions(memory.get('emotions', {})),
                is_lucid=True,  # Mơ tỉnh
                creativity_score=0.6
            )
            self.current_dream_session.add_fragment(fragment)
            await asyncio.sleep(self.fragment_generation_interval)
    
    async def _phase_memory_consolidation(self):
        """Củng cố ký ức quan trọng"""
        logger.debug("Phase: Memory Consolidation - Strengthening important memories...")
        
        # Xác định ký ức quan trọng (xuất hiện nhiều lần, cảm xúc mạnh)
        important_memories = await self.memory_system.get_important_memories()
        
        for memory in important_memories:
            self.current_dream_session.consolidated_memories.append(memory.get('id', ''))
            
            # Tạo fragment củng cố
            fragment = DreamFragment(
                fragment_id=f"frag_{len(self.current_dream_session.fragments)}",
                source_memory_ids=[memory.get('id', '')],
                content=f"[Consolidating] {memory.get('content', '')[:60]}",
                emotion_tone=memory.get('emotions', {}),
                is_lucid=True,
                creativity_score=0.3
            )
            self.current_dream_session.add_fragment(fragment)
        
        # Lưu lại vào memory system
        if self.current_dream_session.consolidated_memories:
            await self.memory_system.strengthen_memories(
                self.current_dream_session.consolidated_memories
            )
            logger.info(f"Strengthened {len(self.current_dream_session.consolidated_memories)} memories")
    
    async def _phase_pattern_discovery(self):
        """Phát hiện mẫu hành vi"""
        logger.debug("Phase: Pattern Discovery - Finding behavioral patterns...")
        
        # Phân tích ký ức để tìm mẫu
        patterns = await self._analyze_behavioral_patterns()
        
        for pattern in patterns:
            self.current_dream_session.patterns_discovered.append(pattern)
            
            fragment = DreamFragment(
                fragment_id=f"frag_{len(self.current_dream_session.fragments)}",
                source_memory_ids=pattern.get('memory_ids', []),
                content=f"[Pattern] {pattern.get('description', '')}",
                emotion_tone={"curiosity": 0.8},
                is_lucid=True,
                creativity_score=0.7
            )
            self.current_dream_session.add_fragment(fragment)
            
            # Tạo insight
            insight = f"Discovered pattern: {pattern.get('description', '')}"
            self.current_dream_session.add_insight(insight)
            
            await asyncio.sleep(1)
    
    async def _phase_creative_synthesis(self):
        """Tổng hợp sáng tạo - tạo ý tưởng mới"""
        logger.debug("Phase: Creative Synthesis - Generating creative ideas...")
        
        # Kết hợp ngẫu nhiên các ký ức để tạo ý tưởng mới
        all_memories = await self.memory_system.search_memories("", n_results=50)
        
        for _ in range(5):  # Tạo 5 ý tưởng sáng tạo
            selected = random.sample(all_memories, min(3, len(all_memories)))
            
            # Tạo tổng hợp sáng tạo
            creative_content = self._synthesize_creative_idea(selected)
            
            fragment = DreamFragment(
                fragment_id=f"frag_{len(self.current_dream_session.fragments)}",
                source_memory_ids=[m.get('id', '') for m in selected],
                content=f"[Creative] {creative_content}",
                emotion_tone={"excitement": 0.9, "curiosity": 0.7},
                is_lucid=True,
                creativity_score=0.9
            )
            self.current_dream_session.add_fragment(fragment)
            
            insight = f"Creative insight: {creative_content}"
            self.current_dream_session.add_insight(insight)
            
            await asyncio.sleep(2)
    
    async def _phase_awakening(self):
        """Giai đoạn thức dậy"""
        logger.debug("Phase: Awakening - Preparing to wake up...")
        
        # Tóm tắt những gì đã học được
        summary = self._generate_dream_summary()
        logger.info(f"🌅 Dream summary: {summary}")
        
        # Lưu insights vào memory
        for insight in self.current_dream_session.insights:
            await self.memory_system.add_memory(
                text=f"[Dream Insight] {insight}",
                metadata={"source": "dream", "session": self.current_dream_session.session_id}
            )
    
    def _blend_emotions(self, emotions1: Dict[str, float], emotions2: Dict[str, float]) -> Dict[str, float]:
        """Trộn hai tập cảm xúc"""
        result = emotions1.copy()
        for emotion, intensity in emotions2.items():
            result[emotion] = result.get(emotion, 0) + intensity * 0.5
        return result
    
    def _process_emotions(self, emotions: Dict[str, float]) -> Dict[str, float]:
        """Xử lý và làm dịu cảm xúc"""
        processed = {}
        for emotion, intensity in emotions.items():
            # Giảm cường độ cảm xúc tiêu cực
            if emotion in ['anger', 'fear', 'sadness']:
                processed[emotion] = intensity * 0.6
            else:
                processed[emotion] = intensity
        return processed
    
    async def _analyze_behavioral_patterns(self) -> List[Dict]:
        """Phân tích để tìm mẫu hành vi"""
        patterns = []
        
        # Placeholder - thực tế sẽ phân tích sâu hơn
        patterns.append({
            "description": "User tends to work late at night",
            "memory_ids": [],
            "confidence": 0.7
        })
        
        patterns.append({
            "description": "User prefers music when coding",
            "memory_ids": [],
            "confidence": 0.6
        })
        
        return patterns
    
    def _synthesize_creative_idea(self, memories: List[Dict]) -> str:
        """Tổng hợp ý tưởng sáng tạo từ ký ức"""
        # Placeholder cho logic sáng tạo
        topics = [m.get('content', '')[:30] for m in memories]
        return f"Combining {len(topics)} concepts into something new..."
    
    def _generate_dream_summary(self) -> str:
        """Tạo tóm tắt giấc mơ"""
        session = self.current_dream_session
        return (
            f"Dream session {session.session_id}: "
            f"{len(session.fragments)} fragments, "
            f"{len(session.insights)} insights, "
            f"{len(session.patterns_discovered)} patterns, "
            f"Duration: {session.duration():.1f}s"
        )
    
    async def wake_up_from_dream(self):
        """Đánh thức khỏi giấc mơ"""
        if self.current_dream_session:
            self.current_dream_session.end_time = time.time()
            self.dream_history.append(self.current_dream_session)
            logger.info(f"⏰ Woken up from dream. Duration: {self.current_dream_session.duration():.1f}s")
            self.current_dream_session = None
        
        self.is_dreaming = False
        self.idle_start_time = None
    
    def get_dream_status(self) -> Dict[str, Any]:
        """Lấy trạng thái giấc mơ hiện tại"""
        return {
            "is_dreaming": self.is_dreaming,
            "current_session": self.current_dream_session.session_id if self.current_dream_session else None,
            "total_dreams": len(self.dream_history),
            "idle_duration": time.time() - self.idle_start_time if self.idle_start_time else 0
        }

# Singleton instance
dream_system = None

def initialize_dream_system(memory_system, emotion_engine):
    global dream_system
    dream_system = DreamSystem(memory_system, emotion_engine)
    return dream_system
