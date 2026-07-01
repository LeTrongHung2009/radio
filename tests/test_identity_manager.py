"""Tests for MyCompanion/companion/identity/identity_manager.py"""

import importlib.util
import sys
import os
import json
import tempfile

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'MyCompanion', 'companion', 'identity', 'identity_manager.py'
)
_spec = importlib.util.spec_from_file_location("identity_manager", _mod_path)
identity_manager = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(identity_manager)

IdentityManager = identity_manager.IdentityManager


class TestIdentityManagerInit:
    def test_default_init(self):
        mgr = IdentityManager()
        assert mgr.identity_data == {}
        assert mgr.canonical_data == {}
        assert mgr.user_relationship["interaction_count"] == 0
        assert mgr.user_relationship["trust_level"] == 0.5
        assert mgr.user_relationship["intimacy_depth"] == 0.0

    def test_custom_path(self):
        mgr = IdentityManager(identity_path="/custom/path.json")
        assert mgr.identity_path == "/custom/path.json"


class TestIdentityManagerLoad:
    def _write_identity_file(self, data):
        f = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(data, f)
        f.close()
        return f.name

    def test_load_identity_success(self):
        data = {
            "identity": {"name": "Miku", "nickname": "Miku-chan"},
            "canonical_data": {"age": 16},
            "personality_core": {"traits": ["cheerful"]},
            "ethical_guidelines": {"core_values": ["kindness"]},
        }
        path = self._write_identity_file(data)
        try:
            mgr = IdentityManager()
            result = mgr.load_identity(path)
            assert result is True
            assert mgr.get_name() == "Miku"
            assert mgr.get_nickname() == "Miku-chan"
            assert mgr.canonical_data["age"] == 16
        finally:
            os.unlink(path)

    def test_load_identity_file_not_found(self):
        mgr = IdentityManager()
        result = mgr.load_identity("/nonexistent/file.json")
        assert result is False

    def test_load_identity_invalid_json(self):
        f = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        f.write("{invalid json")
        f.close()
        try:
            mgr = IdentityManager()
            result = mgr.load_identity(f.name)
            assert result is False
        finally:
            os.unlink(f.name)

    def test_load_identity_missing_fields_sets_defaults(self):
        data = {"identity": {"name": "Test"}}
        path = self._write_identity_file(data)
        try:
            mgr = IdentityManager()
            result = mgr.load_identity(path)
            assert result is True
            assert "core_values" in mgr.ethical_guidelines
        finally:
            os.unlink(path)


class TestIdentityManagerGetters:
    def _make_loaded_manager(self):
        mgr = IdentityManager()
        mgr.identity_data = {
            "identity": {
                "name": "Hatsune Miku",
                "nickname": "Miku",
                "japanese_name": "?????",
                "title": "Virtual Singer",
            },
            "canonical_data": {"hair_color": "teal"},
            "personality_core": {
                "archetype": "Genki Girl",
                "traits": ["cheerful", "kind"],
                "speaking_style": {
                    "tone": "warm",
                    "catchphrases": ["miku miku!"],
                },
            },
            "knowledge_base": {
                "expertise": ["singing", "dancing"],
                "interests": ["music", "leeks"],
                "favorite_things": {"food": "leeks"},
            },
            "ethical_guidelines": {
                "core_values": ["be kind"],
                "conversation_principles": ["listen"],
            },
            "background_lore": {
                "philosophy": "connect through music",
            },
            "voice_characteristics": {"pitch": "high"},
        }
        mgr.canonical_data = mgr.identity_data["canonical_data"]
        mgr.personality_core = mgr.identity_data["personality_core"]
        mgr.knowledge_base = mgr.identity_data["knowledge_base"]
        mgr.ethical_guidelines = mgr.identity_data["ethical_guidelines"]
        return mgr

    def test_get_name(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_name() == "Hatsune Miku"

    def test_get_name_default(self):
        mgr = IdentityManager()
        assert mgr.get_name() == "Miku"

    def test_get_nickname(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_nickname() == "Miku"

    def test_get_japanese_name(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_japanese_name() == "?????"

    def test_get_title(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_title() == "Virtual Singer"

    def test_get_canonical_attribute(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_canonical_attribute("hair_color") == "teal"
        assert mgr.get_canonical_attribute("nonexistent") is None

    def test_get_personality_trait(self):
        mgr = self._make_loaded_manager()
        assert "cheerful" in mgr.get_personality_trait()

    def test_get_speaking_style(self):
        mgr = self._make_loaded_manager()
        style = mgr.get_speaking_style()
        assert style["tone"] == "warm"

    def test_get_catchphrases(self):
        mgr = self._make_loaded_manager()
        assert "miku miku!" in mgr.get_catchphrases()

    def test_get_expertise(self):
        mgr = self._make_loaded_manager()
        assert "singing" in mgr.get_expertise()

    def test_get_interests(self):
        mgr = self._make_loaded_manager()
        assert "music" in mgr.get_interests()

    def test_get_favorites(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_favorites()["food"] == "leeks"

    def test_get_ethical_values(self):
        mgr = self._make_loaded_manager()
        assert "be kind" in mgr.get_ethical_values()

    def test_get_philosophy(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_philosophy() == "connect through music"

    def test_get_voice_preferences(self):
        mgr = self._make_loaded_manager()
        assert mgr.get_voice_preferences()["pitch"] == "high"

    def test_get_identity_context(self):
        mgr = self._make_loaded_manager()
        ctx = mgr.get_identity_context()
        assert ctx["basic_info"]["name"] == "Hatsune Miku"
        assert "personality" in ctx
        assert "knowledge" in ctx
        assert "ethics" in ctx
        assert "relationship" in ctx


class TestIdentityManagerRelationship:
    def test_update_relationship_increments_count(self):
        mgr = IdentityManager()
        mgr.update_relationship("interaction")
        assert mgr.user_relationship["interaction_count"] == 1
        assert mgr.user_relationship["first_meeting"] is not None
        assert mgr.user_relationship["last_interaction"] is not None

    def test_update_relationship_shared_memory(self):
        mgr = IdentityManager()
        mgr.update_relationship("shared_memory", memory="We played chess", importance=0.9)
        assert len(mgr.user_relationship["shared_memories"]) == 1
        assert mgr.user_relationship["shared_memories"][0]["content"] == "We played chess"

    def test_update_relationship_inside_joke(self):
        mgr = IdentityManager()
        mgr.update_relationship("inside_joke", joke="Leek sword", context="gaming")
        assert len(mgr.user_relationship["inside_jokes"]) == 1

    def test_update_relationship_preference_learned(self):
        mgr = IdentityManager()
        mgr.update_relationship("preference_learned", key="color", value="blue")
        assert "color" in mgr.user_relationship["user_preferences_learned"]

    def test_update_relationship_trust_change(self):
        mgr = IdentityManager()
        initial = mgr.user_relationship["trust_level"]
        mgr.update_relationship("trust_change", delta=0.1)
        assert mgr.user_relationship["trust_level"] == initial + 0.1

    def test_update_relationship_trust_clamped(self):
        mgr = IdentityManager()
        mgr.update_relationship("trust_change", delta=10.0)
        assert mgr.user_relationship["trust_level"] == 1.0
        mgr.update_relationship("trust_change", delta=-20.0)
        assert mgr.user_relationship["trust_level"] == 0.0

    def test_update_relationship_intimacy_change(self):
        mgr = IdentityManager()
        mgr.update_relationship("intimacy_change", delta=0.3)
        assert mgr.user_relationship["intimacy_depth"] == 0.3

    def test_get_relationship_summary(self):
        mgr = IdentityManager()
        mgr.update_relationship("interaction")
        mgr.update_relationship("shared_memory", memory="test")
        summary = mgr.get_relationship_summary()
        assert summary["interaction_count"] == 2
        assert summary["shared_memories_count"] == 1

    def test_check_identity_consistency(self):
        mgr = IdentityManager()
        assert mgr.check_identity_consistency("some statement") is True

    def test_str_representation(self):
        mgr = IdentityManager()
        s = str(mgr)
        assert "IdentityManager" in s
        assert "trust=" in s


class TestIdentityManagerSnapshot:
    def test_save_identity_snapshot(self):
        mgr = IdentityManager()
        mgr.identity_data = {"identity": {"name": "Miku"}}

        with tempfile.NamedTemporaryFile(
            suffix='.json', delete=False
        ) as f:
            path = f.name

        try:
            result = mgr.save_identity_snapshot(path)
            assert result is True
            with open(path, 'r') as f:
                data = json.load(f)
            assert "dynamic_state" in data
        finally:
            os.unlink(path)
