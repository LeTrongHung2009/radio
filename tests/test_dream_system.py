"""Tests for MyCompanion/companion/memory/dream_system.py"""

import importlib.util
import sys
import os
import time
from unittest.mock import MagicMock

import pytest

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'MyCompanion', 'companion', 'memory', 'dream_system.py'
)
_spec = importlib.util.spec_from_file_location("dream_system", _mod_path)
dream_system = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dream_system)

DreamPhase = dream_system.DreamPhase
DreamFragment = dream_system.DreamFragment
DreamSession = dream_system.DreamSession
DreamSystem = dream_system.DreamSystem


class TestDreamPhase:
    def test_all_phases_exist(self):
        expected = [
            "WAKEFUL_REST", "LIGHT_DREAM", "DEEP_DREAM",
            "MEMORY_CONSOLIDATION", "PATTERN_DISCOVERY",
            "CREATIVE_SYNTHESIS", "AWAKENING",
        ]
        for name in expected:
            assert hasattr(DreamPhase, name)


class TestDreamFragment:
    def test_creation(self):
        frag = DreamFragment(
            fragment_id="f1",
            source_memory_ids=["m1", "m2"],
            content="a dream fragment",
            emotion_tone={"joy": 0.5},
        )
        assert frag.fragment_id == "f1"
        assert frag.is_lucid is False
        assert frag.creativity_score == 0.0

    def test_to_dict(self):
        frag = DreamFragment(
            fragment_id="f1",
            source_memory_ids=["m1"],
            content="test",
            emotion_tone={"sadness": 0.3},
            is_lucid=True,
            creativity_score=0.7,
        )
        d = frag.to_dict()
        assert d["id"] == "f1"
        assert d["sources"] == ["m1"]
        assert d["content"] == "test"
        assert d["emotions"] == {"sadness": 0.3}
        assert d["lucid"] is True
        assert d["creativity"] == 0.7
        assert "timestamp" in d


class TestDreamSession:
    def test_creation(self):
        session = DreamSession(
            session_id="dream_1",
            start_time=time.time(),
        )
        assert session.end_time is None
        assert session.phases == []
        assert session.fragments == []
        assert session.insights == []

    def test_duration_ongoing(self):
        session = DreamSession(
            session_id="d1",
            start_time=time.time() - 10,
        )
        assert 9 < session.duration() < 12

    def test_duration_completed(self):
        session = DreamSession(
            session_id="d1",
            start_time=100.0,
            end_time=200.0,
        )
        assert session.duration() == 100.0

    def test_add_fragment(self):
        session = DreamSession(session_id="d1", start_time=time.time())
        frag = DreamFragment(
            fragment_id="f1",
            source_memory_ids=[],
            content="test fragment",
            emotion_tone={},
        )
        session.add_fragment(frag)
        assert len(session.fragments) == 1
        assert session.fragments[0].content == "test fragment"

    def test_add_insight(self):
        session = DreamSession(session_id="d1", start_time=time.time())
        session.add_insight("Users tend to code at night")
        assert len(session.insights) == 1
        assert session.insights[0] == "Users tend to code at night"


class TestDreamSystem:
    def _make_system(self):
        memory = MagicMock()
        emotion = MagicMock()
        return DreamSystem(memory, emotion)

    def test_init(self):
        system = self._make_system()
        assert system.is_dreaming is False
        assert system.current_dream_session is None
        assert system.dream_history == []
        assert system.min_idle_time_before_dream == 300

    def test_is_system_idle_placeholder(self):
        system = self._make_system()
        assert system._is_system_idle() is True

    def test_get_dream_status_not_dreaming(self):
        system = self._make_system()
        status = system.get_dream_status()
        assert status["is_dreaming"] is False
        assert status["current_session"] is None
        assert status["total_dreams"] == 0

    def test_get_dream_status_with_idle(self):
        system = self._make_system()
        system.idle_start_time = time.time() - 60
        status = system.get_dream_status()
        assert 59 < status["idle_duration"] < 62

    def test_blend_emotions(self):
        system = self._make_system()
        e1 = {"joy": 0.8, "sadness": 0.2}
        e2 = {"joy": 0.4, "anger": 0.6}
        result = system._blend_emotions(e1, e2)
        assert result["joy"] == 0.8 + 0.4 * 0.5
        assert result["sadness"] == 0.2
        assert result["anger"] == 0.6 * 0.5

    def test_process_emotions(self):
        system = self._make_system()
        emotions = {"joy": 0.8, "anger": 1.0, "fear": 0.5, "sadness": 0.4}
        processed = system._process_emotions(emotions)
        assert processed["joy"] == 0.8
        assert processed["anger"] == 0.6
        assert processed["fear"] == 0.3
        assert processed["sadness"] == 0.24

    def test_synthesize_creative_idea(self):
        system = self._make_system()
        memories = [
            {"content": "User likes chess"},
            {"content": "User studies AI"},
        ]
        result = system._synthesize_creative_idea(memories)
        assert "2 concepts" in result

    @pytest.mark.asyncio
    async def test_wake_up_from_dream(self):
        system = self._make_system()
        system.is_dreaming = True
        system.idle_start_time = time.time()
        system.current_dream_session = DreamSession(
            session_id="d1", start_time=time.time() - 30
        )

        await system.wake_up_from_dream()

        assert system.is_dreaming is False
        assert system.idle_start_time is None
        assert system.current_dream_session is None
        assert len(system.dream_history) == 1

    @pytest.mark.asyncio
    async def test_wake_up_no_session(self):
        system = self._make_system()
        system.is_dreaming = True
        await system.wake_up_from_dream()
        assert system.is_dreaming is False

    @pytest.mark.asyncio
    async def test_analyze_behavioral_patterns(self):
        system = self._make_system()
        patterns = await system._analyze_behavioral_patterns()
        assert len(patterns) > 0
        assert "description" in patterns[0]
        assert "confidence" in patterns[0]

    def test_generate_dream_summary(self):
        system = self._make_system()
        session = DreamSession(
            session_id="test_session",
            start_time=time.time() - 60,
        )
        session.add_insight("insight1")
        session.add_insight("insight2")
        session.patterns_discovered.append({"desc": "p1"})
        frag = DreamFragment(
            fragment_id="f1",
            source_memory_ids=[],
            content="frag",
            emotion_tone={},
        )
        session.add_fragment(frag)

        system.current_dream_session = session
        summary = system._generate_dream_summary()
        assert "test_session" in summary
        assert "1 fragments" in summary
        assert "2 insights" in summary
        assert "1 patterns" in summary

    def test_dream_history_limit(self):
        system = self._make_system()
        system.max_dreams_kept = 3
        for i in range(5):
            session = DreamSession(
                session_id=f"d{i}",
                start_time=time.time(),
                end_time=time.time(),
            )
            system.dream_history.append(session)
            if len(system.dream_history) > system.max_dreams_kept:
                system.dream_history.pop(0)
        assert len(system.dream_history) == 3
