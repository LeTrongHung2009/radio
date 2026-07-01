"""Tests for companion/streaming/chat_message.py"""

import importlib.util
import sys
import os
from datetime import datetime

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'companion', 'streaming', 'chat_message.py'
)
_spec = importlib.util.spec_from_file_location("chat_message", _mod_path)
chat_message = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chat_message)

ChatPlatform = chat_message.ChatPlatform
ChatUser = chat_message.ChatUser
ChatMessage = chat_message.ChatMessage


class TestChatPlatform:
    def test_platforms_exist(self):
        for name in ["TWITCH", "YOUTUBE", "DISCORD", "CUSTOM"]:
            assert hasattr(ChatPlatform, name)

    def test_platform_values_unique(self):
        values = [p.value for p in ChatPlatform]
        assert len(values) == len(set(values))


class TestChatUser:
    def _make_user(self, **kwargs):
        defaults = {
            "id": "user123",
            "username": "testuser",
            "display_name": "Test User",
            "platform": ChatPlatform.TWITCH,
        }
        defaults.update(kwargs)
        return ChatUser(**defaults)

    def test_default_values(self):
        user = self._make_user()
        assert user.is_moderator is False
        assert user.is_subscriber is False
        assert user.is_vip is False
        assert user.badges == []
        assert user.color is None
        assert user.follower_since is None
        assert user.subscriber_months == 0

    def test_hash_same_id_and_platform(self):
        u1 = self._make_user(id="abc", platform=ChatPlatform.TWITCH)
        u2 = self._make_user(id="abc", platform=ChatPlatform.TWITCH, username="other")
        assert hash(u1) == hash(u2)

    def test_hash_different_platform(self):
        u1 = self._make_user(id="abc", platform=ChatPlatform.TWITCH)
        u2 = self._make_user(id="abc", platform=ChatPlatform.YOUTUBE)
        assert hash(u1) != hash(u2)

    def test_equality_same(self):
        u1 = self._make_user(id="abc", platform=ChatPlatform.TWITCH)
        u2 = self._make_user(id="abc", platform=ChatPlatform.TWITCH, display_name="Other")
        assert u1 == u2

    def test_equality_different_id(self):
        u1 = self._make_user(id="abc")
        u2 = self._make_user(id="def")
        assert u1 != u2

    def test_equality_different_platform(self):
        u1 = self._make_user(id="abc", platform=ChatPlatform.TWITCH)
        u2 = self._make_user(id="abc", platform=ChatPlatform.YOUTUBE)
        assert u1 != u2

    def test_equality_with_non_user(self):
        user = self._make_user()
        assert user != "not a user"
        assert user != 42

    def test_user_in_set(self):
        u1 = self._make_user(id="abc", platform=ChatPlatform.TWITCH)
        u2 = self._make_user(id="abc", platform=ChatPlatform.TWITCH)
        u3 = self._make_user(id="def", platform=ChatPlatform.TWITCH)
        s = {u1, u2, u3}
        assert len(s) == 2

    def test_moderator_flag(self):
        user = self._make_user(is_moderator=True)
        assert user.is_moderator is True

    def test_subscriber_with_months(self):
        user = self._make_user(is_subscriber=True, subscriber_months=12)
        assert user.subscriber_months == 12


class TestChatMessage:
    def _make_user(self, **kwargs):
        defaults = {
            "id": "u1",
            "username": "tester",
            "display_name": "Tester",
            "platform": ChatPlatform.TWITCH,
        }
        defaults.update(kwargs)
        return ChatUser(**defaults)

    def _make_message(self, **kwargs):
        defaults = {
            "id": "msg1",
            "user": self._make_user(),
            "content": "Hello world",
            "timestamp": datetime(2025, 1, 1),
            "platform": ChatPlatform.TWITCH,
        }
        defaults.update(kwargs)
        return ChatMessage(**defaults)

    def test_default_values(self):
        msg = self._make_message()
        assert msg.is_action is False
        assert msg.is_first_message is False
        assert msg.reply_to is None
        assert msg.mentions == []
        assert msg.emotes == []
        assert msg.bits_donated == 0
        assert msg.channel_points == 0
        assert msg.redemption_id is None
        assert msg.raw_data == {}

    def test_is_from_known_user_false(self):
        msg = self._make_message()
        assert msg.is_from_known_user is False

    def test_is_from_known_user_follower(self):
        user = self._make_user(follower_since=datetime(2024, 1, 1))
        msg = self._make_message(user=user)
        assert msg.is_from_known_user is True

    def test_is_from_known_user_subscriber(self):
        user = self._make_user(subscriber_months=3)
        msg = self._make_message(user=user)
        assert msg.is_from_known_user is True

    def test_importance_score_base(self):
        msg = self._make_message()
        assert msg.importance_score == 1.0

    def test_importance_score_moderator(self):
        user = self._make_user(is_moderator=True)
        msg = self._make_message(user=user)
        assert msg.importance_score == 4.0

    def test_importance_score_vip(self):
        user = self._make_user(is_vip=True)
        msg = self._make_message(user=user)
        assert msg.importance_score == 3.0

    def test_importance_score_subscriber(self):
        user = self._make_user(is_subscriber=True, subscriber_months=6)
        msg = self._make_message(user=user)
        assert msg.importance_score == 2.0

    def test_importance_score_subscriber_capped(self):
        user = self._make_user(is_subscriber=True, subscriber_months=24)
        msg = self._make_message(user=user)
        assert msg.importance_score == 3.0

    def test_importance_score_bits(self):
        msg = self._make_message(bits_donated=200)
        assert msg.importance_score == 3.0

    def test_importance_score_bits_capped(self):
        msg = self._make_message(bits_donated=1000)
        assert msg.importance_score == 4.0

    def test_importance_score_first_message(self):
        msg = self._make_message(is_first_message=True)
        assert msg.importance_score == 3.0

    def test_importance_score_mentions(self):
        msg = self._make_message(mentions=["@bot"])
        assert msg.importance_score == 2.0

    def test_importance_score_combined(self):
        user = self._make_user(is_moderator=True, is_vip=True)
        msg = self._make_message(
            user=user,
            is_first_message=True,
            mentions=["@bot"],
        )
        assert msg.importance_score == 9.0

    def test_to_dict(self):
        now = datetime(2025, 6, 15, 10, 0, 0)
        msg = self._make_message(
            id="msg42",
            content="test message",
            timestamp=now,
            bits_donated=50,
        )
        d = msg.to_dict()
        assert d["id"] == "msg42"
        assert d["user_id"] == "u1"
        assert d["username"] == "tester"
        assert d["content"] == "test message"
        assert d["timestamp"] == now.isoformat()
        assert d["platform"] == "TWITCH"
        assert d["is_action"] is False
        assert d["bits_donated"] == 50
        assert "importance_score" in d

    def test_to_dict_includes_importance(self):
        user = self._make_user(is_moderator=True)
        msg = self._make_message(user=user)
        d = msg.to_dict()
        assert d["importance_score"] == 4.0
