"""Tests for MyCompanion/core/event_bus.py"""

import importlib.util
import sys
import os

import pytest

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'MyCompanion', 'core', 'event_bus.py'
)
_spec = importlib.util.spec_from_file_location("event_bus", _mod_path)
event_bus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(event_bus)

Event = event_bus.Event
EventBus = event_bus.EventBus


class TestEvent:
    def test_creation(self):
        ev = Event(
            type="test_event",
            source="test_module",
            payload={"key": "value"},
        )
        assert ev.type == "test_event"
        assert ev.source == "test_module"
        assert ev.payload == {"key": "value"}
        assert ev.priority == 0
        assert ev.event_id is not None
        assert ev.timestamp is not None

    def test_unique_ids(self):
        e1 = Event(type="t", source="s", payload={})
        e2 = Event(type="t", source="s", payload={})
        assert e1.event_id != e2.event_id

    def test_priority(self):
        ev = Event(type="t", source="s", payload={}, priority=3)
        assert ev.priority == 3

    def test_repr(self):
        ev = Event(type="my_event", source="mod", payload={})
        r = repr(ev)
        assert "my_event" in r
        assert "mod" in r


class TestEventBus:
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        EventBus._instance = None
        yield
        EventBus._instance = None

    def test_singleton(self):
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2

    @pytest.mark.asyncio
    async def test_subscribe_and_dispatch(self):
        bus = EventBus()
        results = []

        async def handler(event):
            results.append(event.payload["msg"])

        await bus.subscribe("greeting", handler)

        ev = Event(type="greeting", source="test", payload={"msg": "hello"})
        await bus._dispatch(ev)

        assert results == ["hello"]

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = EventBus()
        results = []

        async def handler1(event):
            results.append("h1")

        async def handler2(event):
            results.append("h2")

        await bus.subscribe("test", handler1)
        await bus.subscribe("test", handler2)

        ev = Event(type="test", source="s", payload={})
        await bus._dispatch(ev)

        assert "h1" in results
        assert "h2" in results

    @pytest.mark.asyncio
    async def test_wildcard_subscriber(self):
        bus = EventBus()
        results = []

        async def global_handler(event):
            results.append(event.type)

        await bus.subscribe("*", global_handler)

        ev = Event(type="any_event", source="s", payload={})
        await bus._dispatch(ev)

        assert results == ["any_event"]

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        results = []

        async def handler(event):
            results.append("called")

        await bus.subscribe("test", handler)
        await bus.unsubscribe("test", handler)

        ev = Event(type="test", source="s", payload={})
        await bus._dispatch(ev)

        assert results == []

    @pytest.mark.asyncio
    async def test_publish_puts_on_queue(self):
        bus = EventBus()
        ev = Event(type="test", source="s", payload={"x": 1})
        await bus.publish(ev)
        assert not bus._queue.empty()

    @pytest.mark.asyncio
    async def test_publish_priority_ordering(self):
        bus = EventBus()
        low = Event(type="low", source="s", payload={}, priority=0)
        high = Event(type="high", source="s", payload={}, priority=3)

        await bus.publish(low)
        await bus.publish(high)

        _, _, first_event = await bus._queue.get()
        assert first_event.type == "high"

    @pytest.mark.asyncio
    async def test_dispatch_no_subscribers(self):
        bus = EventBus()
        ev = Event(type="nobody_listening", source="s", payload={})
        await bus._dispatch(ev)

    @pytest.mark.asyncio
    async def test_dispatch_handler_error_doesnt_crash(self):
        bus = EventBus()
        results = []

        async def bad_handler(event):
            raise RuntimeError("boom")

        async def good_handler(event):
            results.append("ok")

        await bus.subscribe("test", bad_handler)
        await bus.subscribe("test", good_handler)

        ev = Event(type="test", source="s", payload={})
        await bus._dispatch(ev)

        assert "ok" in results

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        bus = EventBus()
        await bus.start()
        assert bus._running is True
        assert bus._task is not None

        await bus.stop()
        assert bus._running is False
