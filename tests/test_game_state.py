"""Tests for companion/games/game_state.py"""

import importlib.util
import sys
import os
from datetime import datetime

# Import directly to avoid __init__.py pulling in heavy deps
_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'companion', 'games', 'game_state.py'
)
_spec = importlib.util.spec_from_file_location("game_state", _mod_path)
game_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(game_state)

GameEventType = game_state.GameEventType
GameAction = game_state.GameAction
GameState = game_state.GameState
GameEvent = game_state.GameEvent


class TestGameEventType:
    def test_all_event_types_exist(self):
        expected = [
            "GAME_STARTED", "GAME_ENDED", "GAME_PAUSED", "GAME_RESUMED",
            "ACTION_EXECUTED", "ACTION_FAILED",
            "STATE_CHANGED", "LOCATION_CHANGED", "INVENTORY_CHANGED",
            "BATTLE_STARTED", "BATTLE_ENDED", "POKEMON_CAUGHT",
            "POKEMON_FAINTED", "LEVEL_UP",
            "MOVE_MADE", "CHECK", "CHECKMATE", "RESIGNATION",
        ]
        for name in expected:
            assert hasattr(GameEventType, name), f"Missing GameEventType.{name}"

    def test_event_types_are_unique(self):
        values = [e.value for e in GameEventType]
        assert len(values) == len(set(values))


class TestGameAction:
    def test_movement_actions(self):
        for action in ["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT"]:
            assert hasattr(GameAction, action)

    def test_battle_actions(self):
        for action in ["ATTACK", "DEFEND", "RUN", "SWITCH_POKEMON"]:
            assert hasattr(GameAction, action)

    def test_chess_actions(self):
        for action in ["CHESS_MOVE", "CHESS_RESIGN", "CHESS_DRAW_OFFER"]:
            assert hasattr(GameAction, action)


class TestGameState:
    def test_default_state(self):
        state = GameState(game_id="test", game_name="Test Game")
        assert state.game_id == "test"
        assert state.game_name == "Test Game"
        assert state.is_active is False
        assert state.is_paused is False
        assert state.inventory == []
        assert state.stats == {}
        assert state.last_action is None
        assert state.party == []
        assert state.badges == []
        assert state.chess_board is None

    def test_to_dict_default(self):
        state = GameState(game_id="chess", game_name="Chess")
        d = state.to_dict()
        assert d["game_id"] == "chess"
        assert d["game_name"] == "Chess"
        assert d["is_active"] is False
        assert d["last_action"] is None
        assert d["last_action_time"] is None
        assert d["session_start"] is None
        assert d["chess_board"] is None

    def test_to_dict_with_action(self):
        now = datetime(2025, 1, 1, 12, 0, 0)
        state = GameState(
            game_id="pokemon",
            game_name="Pokemon",
            is_active=True,
            last_action=GameAction.ATTACK,
            last_action_time=now,
            session_start=now,
            inventory=["potion", "pokeball"],
            badges=["Boulder"],
            party=[{"name": "Pikachu", "level": 25}],
        )
        d = state.to_dict()
        assert d["is_active"] is True
        assert d["last_action"] == "ATTACK"
        assert d["last_action_time"] == now.isoformat()
        assert d["session_start"] == now.isoformat()
        assert d["inventory"] == ["potion", "pokeball"]
        assert d["badges"] == ["Boulder"]
        assert d["party"] == [{"name": "Pikachu", "level": 25}]

    def test_to_dict_chess_fields(self):
        state = GameState(
            game_id="chess",
            game_name="Chess",
            chess_board="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            chess_opponent="Magnus",
            chess_eval=1.5,
        )
        d = state.to_dict()
        assert d["chess_board"] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        assert d["chess_opponent"] == "Magnus"
        assert d["chess_eval"] == 1.5

    def test_playtime_seconds_no_session(self):
        state = GameState(game_id="t", game_name="T")
        assert state.playtime_seconds == 0

    def test_playtime_seconds_with_session(self):
        state = GameState(
            game_id="t",
            game_name="T",
            session_start=datetime.utcnow(),
        )
        assert state.playtime_seconds >= 0
        assert state.playtime_seconds < 5

    def test_playtime_formatted_no_session(self):
        state = GameState(game_id="t", game_name="T")
        assert state.playtime_formatted == "00:00:00"

    def test_playtime_formatted_with_session(self):
        state = GameState(
            game_id="t",
            game_name="T",
            session_start=datetime.utcnow(),
        )
        fmt = state.playtime_formatted
        assert len(fmt) == 8
        assert fmt.count(":") == 2

    def test_inventory_mutable(self):
        state = GameState(game_id="t", game_name="T")
        state.inventory.append("sword")
        assert "sword" in state.inventory

    def test_metadata_mutable(self):
        state = GameState(game_id="t", game_name="T")
        state.metadata["key"] = "value"
        assert state.metadata["key"] == "value"


class TestGameEvent:
    def test_game_event_creation(self):
        now = datetime(2025, 6, 15, 10, 30, 0)
        event = GameEvent(
            event_type=GameEventType.GAME_STARTED,
            game_id="chess",
            timestamp=now,
            data={"player": "user1"},
        )
        assert event.event_type == GameEventType.GAME_STARTED
        assert event.game_id == "chess"
        assert event.timestamp == now
        assert event.data == {"player": "user1"}

    def test_game_event_to_dict(self):
        now = datetime(2025, 6, 15, 10, 30, 0)
        event = GameEvent(
            event_type=GameEventType.CHECKMATE,
            game_id="chess",
            timestamp=now,
        )
        d = event.to_dict()
        assert d["event_type"] == "CHECKMATE"
        assert d["game_id"] == "chess"
        assert d["timestamp"] == now.isoformat()
        assert d["data"] == {}

    def test_game_event_default_data(self):
        event = GameEvent(
            event_type=GameEventType.LEVEL_UP,
            game_id="pokemon",
            timestamp=datetime.utcnow(),
        )
        assert event.data == {}
