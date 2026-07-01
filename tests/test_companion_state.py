"""Tests for MyCompanion/companion/brain/companion_state.py"""

import importlib.util
import sys
import os
import time

import pytest

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'MyCompanion', 'companion', 'brain', 'companion_state.py'
)
_spec = importlib.util.spec_from_file_location("companion_state", _mod_path)
companion_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(companion_state)

ActivityState = companion_state.ActivityState
ConversationTurn = companion_state.ConversationTurn
UserPresence = companion_state.UserPresence
SignalEmitter = companion_state.SignalEmitter
CompanionState = companion_state.CompanionState


class TestActivityState:
    def test_all_states_exist(self):
        for name in ["IDLE", "LISTENING", "THINKING", "SPEAKING",
                      "PROCESSING_VISUAL", "BUSY"]:
            assert hasattr(ActivityState, name)

    def test_values(self):
        assert ActivityState.IDLE.value == "idle"
        assert ActivityState.SPEAKING.value == "speaking"
        assert ActivityState.THINKING.value == "thinking"


class TestConversationTurn:
    def test_creation(self):
        turn = ConversationTurn(
            timestamp=1000.0,
            speaker="user",
            text="Hello",
        )
        assert turn.speaker == "user"
        assert turn.text == "Hello"
        assert turn.emotion is None
        assert turn.metadata == {}

    def test_to_dict(self):
        turn = ConversationTurn(
            timestamp=1000.0,
            speaker="ai",
            text="Hi there",
            emotion="joy",
            metadata={"source": "chat"},
        )
        d = turn.to_dict()
        assert d["timestamp"] == 1000.0
        assert d["speaker"] == "ai"
        assert d["text"] == "Hi there"
        assert d["emotion"] == "joy"
        assert d["metadata"] == {"source": "chat"}


class TestUserPresence:
    def test_defaults(self):
        presence = UserPresence()
        assert presence.is_present is True
        assert presence.active_window is None
        assert presence.is_gaming is False
        assert presence.is_watching_video is False
        assert presence.is_listening_music is False


class TestSignalEmitter:
    def test_connect_and_emit(self):
        emitter = SignalEmitter()
        results = []
        emitter.connect("test_signal", lambda x: results.append(x))
        emitter.emit("test_signal", 42)
        assert results == [42]

    def test_multiple_callbacks(self):
        emitter = SignalEmitter()
        results = []
        emitter.connect("sig", lambda: results.append("a"))
        emitter.connect("sig", lambda: results.append("b"))
        emitter.emit("sig")
        assert results == ["a", "b"]

    def test_emit_no_subscribers(self):
        emitter = SignalEmitter()
        emitter.emit("nonexistent")

    def test_disconnect(self):
        emitter = SignalEmitter()
        results = []
        callback = lambda: results.append("called")
        emitter.connect("sig", callback)
        emitter.disconnect("sig", callback)
        emitter.emit("sig")
        assert results == []

    def test_disconnect_nonexistent_signal(self):
        emitter = SignalEmitter()
        emitter.disconnect("missing", lambda: None)

    def test_emit_error_handling(self):
        emitter = SignalEmitter()
        results = []
        emitter.connect("sig", lambda: 1 / 0)
        emitter.connect("sig", lambda: results.append("ok"))
        emitter.emit("sig")
        assert results == ["ok"]

    @pytest.mark.asyncio
    async def test_emit_async(self):
        emitter = SignalEmitter()
        results = []

        async def async_handler(val):
            results.append(val)

        emitter.connect("sig", async_handler)
        await emitter.emit_async("sig", "hello")
        assert results == ["hello"]

    @pytest.mark.asyncio
    async def test_emit_async_mixed_handlers(self):
        emitter = SignalEmitter()
        results = []

        async def async_handler():
            results.append("async")

        def sync_handler():
            results.append("sync")

        emitter.connect("sig", async_handler)
        emitter.connect("sig", sync_handler)
        await emitter.emit_async("sig")
        assert "async" in results
        assert "sync" in results


class TestCompanionState:
    def test_initial_state(self):
        state = CompanionState()
        assert state.activity == ActivityState.IDLE
        assert state.conversation_history == []
        assert state.boredom_level == 0.0
        assert state.total_messages == 0
        assert state.total_responses == 0

    def test_is_available(self):
        state = CompanionState()
        assert state.is_available() is True
        state.activity = ActivityState.LISTENING
        assert state.is_available() is True
        state.activity = ActivityState.THINKING
        assert state.is_available() is False

    def test_is_busy(self):
        state = CompanionState()
        assert state.is_busy() is False
        state.activity = ActivityState.SPEAKING
        assert state.is_busy() is True
        state.activity = ActivityState.THINKING
        assert state.is_busy() is True
        state.activity = ActivityState.BUSY
        assert state.is_busy() is True

    @pytest.mark.asyncio
    async def test_add_user_message(self):
        state = CompanionState()
        turn = state.add_user_message("Hello!")
        assert turn.speaker == "user"
        assert turn.text == "Hello!"
        assert state.total_messages == 1
        assert len(state.conversation_history) == 1

    @pytest.mark.asyncio
    async def test_add_ai_message(self):
        state = CompanionState()
        turn = state.add_ai_message("Hi there!", emotion="joy")
        assert turn.speaker == "ai"
        assert turn.emotion == "joy"
        assert state.total_responses == 1

    @pytest.mark.asyncio
    async def test_conversation_history_trimmed(self):
        state = CompanionState(max_history=5)
        for i in range(10):
            state.add_user_message(f"msg {i}")
        assert len(state.conversation_history) == 5

    @pytest.mark.asyncio
    async def test_short_term_context_last_10(self):
        state = CompanionState()
        for i in range(15):
            state.add_user_message(f"msg {i}")
        assert len(state.short_term_context) == 10

    @pytest.mark.asyncio
    async def test_get_recent_messages(self):
        state = CompanionState()
        for i in range(20):
            state.add_user_message(f"msg {i}")
        recent = state.get_recent_messages(5)
        assert len(recent) == 5
        assert recent[-1].text == "msg 19"

    @pytest.mark.asyncio
    async def test_get_context_string(self):
        state = CompanionState()
        state.add_user_message("Hello")
        state.add_ai_message("Hi there")
        context = state.get_context_string()
        assert "You: Hello" in context
        assert "Assistant: Hi there" in context

    @pytest.mark.asyncio
    async def test_clear_history(self):
        state = CompanionState()
        state.add_user_message("test")
        state.add_ai_message("reply")
        state.clear_history()
        assert state.conversation_history == []
        assert state.short_term_context == []

    def test_get_idle_duration_not_idle(self):
        state = CompanionState()
        state.idle_start_time = None
        assert state.get_idle_duration() == 0.0

    def test_get_idle_duration_idle(self):
        state = CompanionState()
        state.idle_start_time = time.time() - 10
        duration = state.get_idle_duration()
        assert 9 < duration < 12

    def test_update_boredom(self):
        state = CompanionState()
        state.idle_start_time = time.time() - 30
        level = state.update_boredom(boredom_threshold=60.0)
        assert 0.4 < level < 0.6

    def test_update_boredom_max(self):
        state = CompanionState()
        state.idle_start_time = time.time() - 120
        level = state.update_boredom(boredom_threshold=60.0)
        assert level == 1.0

    def test_reset_boredom(self):
        state = CompanionState()
        state.boredom_level = 0.8
        state.idle_start_time = time.time() - 100
        state.reset_boredom()
        assert state.boredom_level == 0.0
        assert state.idle_start_time is None

    def test_detect_activity_type_gaming(self):
        state = CompanionState()
        state._detect_activity_type("Playing Steam Game")
        assert state.user_presence.is_gaming is True
        assert state.user_presence.is_watching_video is False

    def test_detect_activity_type_video(self):
        state = CompanionState()
        state._detect_activity_type("YouTube - Funny Video")
        assert state.user_presence.is_watching_video is True

    def test_detect_activity_type_music(self):
        state = CompanionState()
        state._detect_activity_type("Spotify - Playing Song")
        assert state.user_presence.is_listening_music is True

    def test_detect_activity_type_none(self):
        state = CompanionState()
        state._detect_activity_type("Visual Studio Code")
        assert state.user_presence.is_gaming is False
        assert state.user_presence.is_watching_video is False
        assert state.user_presence.is_listening_music is False

    @pytest.mark.asyncio
    async def test_custom_state(self):
        state = CompanionState()
        state.set_custom_state("mode", "dark")
        assert state.get_custom_state("mode") == "dark"

    def test_custom_state_default(self):
        state = CompanionState()
        assert state.get_custom_state("missing", "default") == "default"

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        state = CompanionState()
        state.add_user_message("hello")
        state.add_ai_message("hi")
        stats = state.get_statistics()
        assert stats["total_messages"] == 1
        assert stats["total_responses"] == 1
        assert stats["current_activity"] == "idle"
        assert stats["conversation_turns"] == 2
        assert "session_duration_seconds" in stats

    @pytest.mark.asyncio
    async def test_to_dict(self):
        state = CompanionState()
        state.add_user_message("test")
        d = state.to_dict()
        assert d["activity"] == "idle"
        assert "user_presence" in d
        assert "conversation_history" in d
        assert "statistics" in d

    def test_str_representation(self):
        state = CompanionState()
        s = str(state)
        assert "CompanionState" in s
        assert "idle" in s

    @pytest.mark.asyncio
    async def test_set_activity(self):
        state = CompanionState()
        await state.set_activity(ActivityState.THINKING, "processing")
        assert state.activity == ActivityState.THINKING

    @pytest.mark.asyncio
    async def test_set_activity_idle_tracks_time(self):
        state = CompanionState()
        await state.set_activity(ActivityState.SPEAKING)
        assert state.idle_start_time is None
        await state.set_activity(ActivityState.IDLE)
        assert state.idle_start_time is not None

    @pytest.mark.asyncio
    async def test_acquire_and_release_turn(self):
        state = CompanionState()
        acquired = await state.acquire_turn(timeout=1.0)
        assert acquired is True
        state.release_turn()

    @pytest.mark.asyncio
    async def test_start_thinking_and_speaking(self):
        state = CompanionState()
        await state.start_thinking()
        assert state.activity == ActivityState.THINKING
        await state.start_speaking()
        assert state.activity == ActivityState.SPEAKING
        await state.finish_speaking()
        assert state.activity == ActivityState.IDLE

    @pytest.mark.asyncio
    async def test_update_user_presence(self):
        state = CompanionState()
        state.update_user_presence(is_present=True, active_window="Minecraft")
        assert state.user_presence.is_present is True
        assert state.user_presence.active_window == "Minecraft"
        assert state.user_presence.is_gaming is True
