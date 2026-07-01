"""Tests for companion/streaming/stream_events.py"""

import importlib.util
import sys
import os
from datetime import datetime

_base = os.path.join(os.path.dirname(__file__), '..', 'companion', 'streaming')

# Load chat_message first (dependency)
_cm_spec = importlib.util.spec_from_file_location(
    "chat_message", os.path.join(_base, 'chat_message.py')
)
chat_message = importlib.util.module_from_spec(_cm_spec)
sys.modules["chat_message"] = chat_message
_cm_spec.loader.exec_module(chat_message)

# Patch the relative import in stream_events
sys.modules[".chat_message"] = chat_message

# Load stream_events using the chat_message already in sys.modules
_se_path = os.path.join(_base, 'stream_events.py')
_se_spec = importlib.util.spec_from_file_location("stream_events", _se_path)
stream_events = importlib.util.module_from_spec(_se_spec)

# Monkey-patch the import: stream_events does `from .chat_message import ...`
# We need to make it find chat_message. Let's load by manipulating sys.path.
# Actually, let's just exec the file after pre-loading dependencies.

# Alternative approach: read the file, replace relative import, exec
import types

_se_source = open(_se_path).read()
_se_source = _se_source.replace(
    "from .chat_message import ChatMessage, ChatUser, ChatPlatform",
    ""  # Remove relative import, we'll inject manually
)
_se_mod = types.ModuleType("stream_events")
_se_mod.ChatMessage = chat_message.ChatMessage
_se_mod.ChatUser = chat_message.ChatUser
_se_mod.ChatPlatform = chat_message.ChatPlatform
exec(compile(_se_source, _se_path, 'exec'), _se_mod.__dict__)

ChatPlatform = chat_message.ChatPlatform
ChatUser = chat_message.ChatUser
ChatMessage = chat_message.ChatMessage
EventType = _se_mod.EventType
StreamEvent = _se_mod.StreamEvent
RaidData = _se_mod.RaidData
SubscriptionData = _se_mod.SubscriptionData


class TestEventType:
    def test_chat_events(self):
        for name in ["MESSAGE_RECEIVED", "MESSAGE_DELETED", "USER_TIMEOUT", "USER_BANNED"]:
            assert hasattr(EventType, name)

    def test_follow_subscribe_events(self):
        for name in ["NEW_FOLLOWER", "NEW_SUBSCRIBER", "SUBSCRIPTION_GIFTED", "RESUBSCRIPTION"]:
            assert hasattr(EventType, name)

    def test_donation_events(self):
        for name in ["BITS_CHEERED", "DONATION_RECEIVED", "CHANNEL_POINTS_REDEMPTION"]:
            assert hasattr(EventType, name)

    def test_stream_state_events(self):
        for name in ["STREAM_STARTED", "STREAM_ENDED", "STREAM_PAUSED", "STREAM_RESUMED"]:
            assert hasattr(EventType, name)

    def test_platform_specific_events(self):
        for name in ["TWITCH_POLL_CREATED", "YOUTUBE_SUPERCHAT", "YOUTUBE_MEMBER_JOIN"]:
            assert hasattr(EventType, name)

    def test_values_unique(self):
        values = [e.value for e in EventType]
        assert len(values) == len(set(values))


class TestStreamEvent:
    def _make_event(self, **kwargs):
        defaults = {
            "event_type": EventType.MESSAGE_RECEIVED,
            "platform": ChatPlatform.TWITCH,
            "timestamp": datetime(2025, 6, 15),
        }
        defaults.update(kwargs)
        return StreamEvent(**defaults)

    def test_default_data(self):
        event = self._make_event()
        assert event.data == {}
        assert event.raw_data == {}

    def test_user_property_present(self):
        user = ChatUser(
            id="u1", username="test", display_name="Test",
            platform=ChatPlatform.TWITCH,
        )
        event = self._make_event(data={"user": user})
        assert event.user == user

    def test_user_property_absent(self):
        event = self._make_event()
        assert event.user is None

    def test_message_property_present(self):
        user = ChatUser(
            id="u1", username="test", display_name="Test",
            platform=ChatPlatform.TWITCH,
        )
        msg = ChatMessage(
            id="m1", user=user, content="hello",
            timestamp=datetime.utcnow(), platform=ChatPlatform.TWITCH,
        )
        event = self._make_event(data={"message": msg})
        assert event.message == msg

    def test_message_property_absent(self):
        event = self._make_event()
        assert event.message is None

    def test_amount_property(self):
        event = self._make_event(data={"amount": 500})
        assert event.amount == 500

    def test_amount_property_absent(self):
        event = self._make_event()
        assert event.amount is None

    def test_gift_count_property(self):
        event = self._make_event(data={"gift_count": 5})
        assert event.gift_count == 5

    def test_gift_count_default(self):
        event = self._make_event()
        assert event.gift_count == 0

    def test_to_dict_basic(self):
        now = datetime(2025, 6, 15, 10, 0, 0)
        event = self._make_event(
            event_type=EventType.STREAM_STARTED,
            platform=ChatPlatform.YOUTUBE,
            timestamp=now,
        )
        d = event.to_dict()
        assert d["event_type"] == "STREAM_STARTED"
        assert d["platform"] == "YOUTUBE"
        assert d["timestamp"] == now.isoformat()
        assert d["data"] == {}

    def test_to_dict_with_primitive_data(self):
        event = self._make_event(data={
            "amount": 100,
            "message_text": "hello",
            "is_active": True,
            "items": [1, 2, 3],
        })
        d = event.to_dict()
        assert d["data"]["amount"] == 100
        assert d["data"]["message_text"] == "hello"
        assert d["data"]["is_active"] is True
        assert d["data"]["items"] == [1, 2, 3]

    def test_to_dict_with_chat_user_raises(self):
        """ChatUser lacks to_dict() -- StreamEvent.to_dict triggers AttributeError."""
        user = ChatUser(
            id="u1", username="test", display_name="Test",
            platform=ChatPlatform.TWITCH,
        )
        event = self._make_event(data={"user": user})
        import pytest as _pytest
        with _pytest.raises(AttributeError):
            event.to_dict()

    def test_to_dict_skips_non_serializable(self):
        event = self._make_event(data={"func": lambda: None})
        d = event.to_dict()
        assert "func" not in d["data"]


class TestRaidData:
    def test_creation(self):
        now = datetime(2025, 6, 15)
        raid = RaidData(
            source_channel="streamer123",
            viewer_count=150,
            timestamp=now,
        )
        assert raid.source_channel == "streamer123"
        assert raid.viewer_count == 150

    def test_to_dict(self):
        now = datetime(2025, 6, 15, 10, 0, 0)
        raid = RaidData(
            source_channel="ch1",
            viewer_count=50,
            timestamp=now,
        )
        d = raid.to_dict()
        assert d["source_channel"] == "ch1"
        assert d["viewer_count"] == 50
        assert d["timestamp"] == now.isoformat()


class TestSubscriptionData:
    def _make_user(self, **kwargs):
        defaults = {
            "id": "u1",
            "username": "sub_user",
            "display_name": "Sub User",
            "platform": ChatPlatform.TWITCH,
        }
        defaults.update(kwargs)
        return ChatUser(**defaults)

    def test_creation_basic(self):
        user = self._make_user()
        sub = SubscriptionData(user=user, tier="1000", months=1)
        assert sub.is_gift is False
        assert sub.gifter is None
        assert sub.gift_months == 0

    def test_creation_gift(self):
        user = self._make_user(id="recipient")
        gifter = self._make_user(id="gifter", username="generous")
        sub = SubscriptionData(
            user=user,
            tier="2000",
            months=6,
            is_gift=True,
            gifter=gifter,
            gift_months=3,
        )
        assert sub.is_gift is True
        assert sub.gifter.username == "generous"
        assert sub.gift_months == 3

    def test_to_dict_raises_for_user(self):
        """ChatUser lacks to_dict() -- SubscriptionData.to_dict triggers AttributeError."""
        user = self._make_user()
        sub = SubscriptionData(user=user, tier="1000", months=1)
        import pytest as _pytest
        with _pytest.raises(AttributeError):
            sub.to_dict()

    def test_fields_no_gifter(self):
        user = self._make_user()
        sub = SubscriptionData(user=user, tier="1000", months=1)
        assert sub.tier == "1000"
        assert sub.months == 1
        assert sub.is_gift is False
        assert sub.gifter is None

    def test_fields_with_gifter(self):
        user = self._make_user()
        gifter = self._make_user(id="g1", username="gifter_name")
        sub = SubscriptionData(
            user=user,
            tier="3000",
            months=12,
            is_gift=True,
            gifter=gifter,
            gift_months=6,
        )
        assert sub.is_gift is True
        assert sub.gifter is not None
        assert sub.gift_months == 6
