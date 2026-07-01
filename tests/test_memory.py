"""Tests for MyCompanion/companion/memory/memory.py"""

import importlib.util
import sys
import os
import json
import tempfile
import shutil

import pytest

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'MyCompanion', 'companion', 'memory', 'memory.py'
)
_spec = importlib.util.spec_from_file_location("memory", _mod_path)
memory_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(memory_mod)

ConversationTurn = memory_mod.ConversationTurn
MemoryManager = memory_mod.MemoryManager


class TestConversationTurn:
    def test_creation(self):
        turn = ConversationTurn(
            timestamp=1000.0,
            user_message="Hello",
            ai_response="Hi there",
            emotion="joy",
        )
        assert turn.user_message == "Hello"
        assert turn.ai_response == "Hi there"
        assert turn.emotion == "joy"
        assert turn.context == ""


class TestMemoryManager:
    @pytest.fixture
    def temp_dir(self):
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir, monkeypatch):
        monkeypatch.chdir(temp_dir)
        mgr = MemoryManager()
        return mgr

    def test_init(self, manager):
        assert manager.recent_turns == []
        assert manager.facts == []
        assert manager.turns_stored == 0
        assert manager.facts_extracted == 0

    @pytest.mark.asyncio
    async def test_add_turn(self, manager):
        await manager.add_turn("Hello", "Hi", "joy")
        assert len(manager.recent_turns) == 1
        assert manager.turns_stored == 1
        assert manager.recent_turns[0].user_message == "Hello"

    @pytest.mark.asyncio
    async def test_add_turn_trims_excess(self, manager):
        manager.max_recent_turns = 5
        for i in range(10):
            await manager.add_turn(f"msg {i}", f"reply {i}", "neutral")
        assert len(manager.recent_turns) == 5
        assert manager.turns_stored == 10
        assert manager.recent_turns[0].user_message == "msg 5"

    @pytest.mark.asyncio
    async def test_get_recent_turns(self, manager):
        for i in range(5):
            await manager.add_turn(f"msg {i}", f"reply {i}", "neutral")
        recent = await manager.get_recent_turns(3)
        assert len(recent) == 3
        assert recent[-1].user_message == "msg 4"

    @pytest.mark.asyncio
    async def test_extract_facts_name(self, manager):
        await manager.extract_facts("My name is Alice. How are you?")
        assert len(manager.facts) >= 1
        assert any("Alice" in f["text"] for f in manager.facts)
        assert manager.facts_extracted >= 1

    @pytest.mark.asyncio
    async def test_extract_facts_like(self, manager):
        await manager.extract_facts("I like playing chess.")
        assert any("chess" in f["text"] for f in manager.facts)

    @pytest.mark.asyncio
    async def test_extract_facts_no_match(self, manager):
        await manager.extract_facts("The weather is nice today.")
        assert len(manager.facts) == 0

    @pytest.mark.asyncio
    async def test_extract_facts_no_duplicates(self, manager):
        await manager.extract_facts("My name is Bob")
        await manager.extract_facts("My name is Bob")
        name_facts = [f for f in manager.facts if "Bob" in f["text"]]
        assert len(name_facts) == 1

    @pytest.mark.asyncio
    async def test_add_fact(self, manager):
        await manager.add_fact("User likes cats", confidence=0.9)
        assert len(manager.facts) == 1
        assert manager.facts[0]["text"] == "User likes cats"
        assert manager.facts[0]["confidence"] == 0.9
        assert manager.facts[0]["source"] == "manual"

    @pytest.mark.asyncio
    async def test_search_facts(self, manager):
        await manager.add_fact("User likes cats")
        await manager.add_fact("User works at Google")
        await manager.add_fact("User plays chess")

        results = await manager.search_facts("cats")
        assert len(results) == 1
        assert results[0]["text"] == "User likes cats"

    @pytest.mark.asyncio
    async def test_search_facts_no_match(self, manager):
        await manager.add_fact("User likes cats")
        results = await manager.search_facts("dogs")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_facts_case_insensitive(self, manager):
        await manager.add_fact("User likes CATS")
        results = await manager.search_facts("cats")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_clear_recent_history(self, manager):
        await manager.add_turn("msg", "reply", "neutral")
        await manager.clear_recent_history()
        assert manager.recent_turns == []

    @pytest.mark.asyncio
    async def test_save_and_load_facts(self, manager):
        await manager.add_fact("Persistent fact")
        await manager.save()

        assert manager.facts_file.exists()
        with open(manager.facts_file, 'r') as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["text"] == "Persistent fact"

    @pytest.mark.asyncio
    async def test_save_creates_sessions_file(self, manager):
        await manager.save()
        assert manager.sessions_file.exists()
        with open(manager.sessions_file, 'r') as f:
            data = json.load(f)
        assert "total_turns" in data
        assert "last_session" in data

    @pytest.mark.asyncio
    async def test_initialize_loads_existing_facts(self, manager):
        facts_data = [
            {"text": "fact1", "timestamp": 1000, "confidence": 0.8, "source": "test"}
        ]
        with open(manager.facts_file, 'w') as f:
            json.dump(facts_data, f)

        await manager.initialize()
        assert len(manager.facts) == 1
        assert manager.facts[0]["text"] == "fact1"

    @pytest.mark.asyncio
    async def test_initialize_loads_identity(self, manager):
        identity_data = {"name": "TestUser", "age": 25}
        with open(manager.identity_file, 'w') as f:
            json.dump(identity_data, f)

        await manager.initialize()
        assert manager.identity["name"] == "TestUser"

    @pytest.mark.asyncio
    async def test_update_identity(self, manager):
        await manager.update_identity("name", "Alice")
        assert manager.identity["name"] == "Alice"
        with open(manager.identity_file, 'r') as f:
            data = json.load(f)
        assert data["name"] == "Alice"

    def test_get_stats(self, manager):
        stats = manager.get_stats()
        assert stats["recent_turns"] == 0
        assert stats["total_turns_stored"] == 0
        assert stats["facts_count"] == 0
        assert stats["facts_extracted"] == 0
        assert stats["max_recent_turns"] == 100
