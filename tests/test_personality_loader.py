"""Tests for MyCompanion/companion/persona/personality_loader.py"""

import importlib.util
import sys
import os
import json
import tempfile

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'MyCompanion', 'companion', 'persona', 'personality_loader.py'
)
_spec = importlib.util.spec_from_file_location("personality_loader", _mod_path)
personality_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(personality_loader)

PersonalityConfig = personality_loader.PersonalityConfig
PersonalityLoader = personality_loader.PersonalityLoader


class TestPersonalityConfig:
    def test_defaults(self):
        config = PersonalityConfig(name="Test", archetype="Neutral")
        assert config.name == "Test"
        assert config.archetype == "Neutral"
        assert config.traits == []
        assert config.energy_level == 0.7
        assert config.openness == 0.8
        assert config.empathy == 0.75
        assert config.humor == 0.6

    def test_to_dict(self):
        config = PersonalityConfig(
            name="Miku",
            archetype="Genki",
            traits=["Cheerful", "Kind"],
            interests=["Music"],
        )
        d = config.to_dict()
        assert d["name"] == "Miku"
        assert d["archetype"] == "Genki"
        assert d["traits"] == ["Cheerful", "Kind"]
        assert d["interests"] == ["Music"]
        assert "dynamic_params" in d
        assert d["dynamic_params"]["energy_level"] == 0.7


class TestPersonalityLoader:
    def test_init_defaults(self):
        loader = PersonalityLoader()
        assert loader.active_profile is None
        assert loader.profiles == {}

    def test_init_custom_path(self):
        loader = PersonalityLoader(default_path="/custom/path.yaml")
        assert loader.default_path == "/custom/path.yaml"

    def test_load_profile_json(self):
        data = {
            "name": "TestBot",
            "archetype": "Helper",
            "traits": ["Friendly"],
            "energy_level": 0.9,
            "openness": 0.5,
        }
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(data, f)
            path = f.name

        try:
            loader = PersonalityLoader()
            config = loader.load_profile(path)
            assert config is not None
            assert config.name == "TestBot"
            assert config.archetype == "Helper"
            assert config.traits == ["Friendly"]
            assert config.energy_level == 0.9
            assert config.openness == 0.5
            assert "TestBot" in loader.profiles
            assert loader.active_profile == config
        finally:
            os.unlink(path)

    def test_load_profile_yaml(self):
        import yaml
        data = {
            "name": "YamlBot",
            "archetype": "Calm",
            "traits": ["Patient"],
        }
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump(data, f)
            path = f.name

        try:
            loader = PersonalityLoader()
            config = loader.load_profile(path)
            assert config is not None
            assert config.name == "YamlBot"
        finally:
            os.unlink(path)

    def test_load_profile_not_found(self):
        loader = PersonalityLoader()
        config = loader.load_profile("/nonexistent/path.json")
        assert config is None

    def test_load_profile_invalid_json(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            f.write("not valid json{{{")
            path = f.name

        try:
            loader = PersonalityLoader()
            config = loader.load_profile(path)
            assert config is None
        finally:
            os.unlink(path)

    def test_load_profile_with_name_override(self):
        data = {"name": "Original", "archetype": "A"}
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(data, f)
            path = f.name

        try:
            loader = PersonalityLoader()
            config = loader.load_profile(path, profile_name="Override")
            assert config.name == "Override"
            assert "Override" in loader.profiles
        finally:
            os.unlink(path)

    def test_set_active_profile(self):
        loader = PersonalityLoader()
        loader.profiles["A"] = PersonalityConfig(name="A", archetype="X")
        loader.profiles["B"] = PersonalityConfig(name="B", archetype="Y")
        loader.active_profile = loader.profiles["A"]

        assert loader.set_active_profile("B") is True
        assert loader.active_profile.name == "B"

    def test_set_active_profile_not_found(self):
        loader = PersonalityLoader()
        assert loader.set_active_profile("missing") is False

    def test_adjust_parameter_valid(self):
        loader = PersonalityLoader()
        loader.active_profile = PersonalityConfig(name="T", archetype="T")

        assert loader.adjust_parameter("energy_level", 0.5) is True
        assert loader.active_profile.energy_level == 0.5
        assert "energy_level" in loader.custom_adjustments

    def test_adjust_parameter_invalid_name(self):
        loader = PersonalityLoader()
        loader.active_profile = PersonalityConfig(name="T", archetype="T")
        assert loader.adjust_parameter("invalid_param", 0.5) is False

    def test_adjust_parameter_out_of_range(self):
        loader = PersonalityLoader()
        loader.active_profile = PersonalityConfig(name="T", archetype="T")
        assert loader.adjust_parameter("energy_level", 1.5) is False
        assert loader.adjust_parameter("energy_level", -0.1) is False

    def test_adjust_parameter_no_profile(self):
        loader = PersonalityLoader()
        assert loader.adjust_parameter("energy_level", 0.5) is False

    def test_get_trait(self):
        loader = PersonalityLoader()
        loader.active_profile = PersonalityConfig(
            name="T", archetype="T", traits=["Friendly", "Kind"]
        )
        assert loader.get_trait("Friendly") is True
        assert loader.get_trait("Mean") is False

    def test_get_trait_no_profile(self):
        loader = PersonalityLoader()
        assert loader.get_trait("anything") is False

    def test_get_speaking_pattern(self):
        loader = PersonalityLoader()
        loader.active_profile = PersonalityConfig(
            name="T", archetype="T",
            response_patterns={"greeting": "Hello!"},
        )
        assert loader.get_speaking_pattern("greeting") == "Hello!"
        assert loader.get_speaking_pattern("unknown") == ""

    def test_get_speaking_pattern_no_profile(self):
        loader = PersonalityLoader()
        assert loader.get_speaking_pattern("greeting") == ""

    def test_get_emotional_baseline(self):
        loader = PersonalityLoader()
        loader.active_profile = PersonalityConfig(
            name="T", archetype="T",
            emotional_baseline={"joy": 0.8},
        )
        assert loader.get_emotional_baseline("joy") == 0.8
        assert loader.get_emotional_baseline("anger") == 0.5

    def test_get_all_profiles(self):
        loader = PersonalityLoader()
        loader.profiles["A"] = PersonalityConfig(name="A", archetype="X")
        loader.profiles["B"] = PersonalityConfig(name="B", archetype="Y")
        names = loader.get_all_profiles()
        assert "A" in names
        assert "B" in names

    def test_get_active_profile_name(self):
        loader = PersonalityLoader()
        assert loader.get_active_profile_name() == "None"
        loader.active_profile = PersonalityConfig(name="Miku", archetype="T")
        assert loader.get_active_profile_name() == "Miku"

    def test_export_profile_json(self):
        loader = PersonalityLoader()
        loader.profiles["TestExport"] = PersonalityConfig(
            name="TestExport", archetype="X", traits=["A"]
        )

        with tempfile.NamedTemporaryFile(
            suffix='.json', delete=False
        ) as f:
            path = f.name

        try:
            result = loader.export_profile("TestExport", path, format='json')
            assert result is True
            with open(path, 'r') as f:
                data = json.load(f)
            assert data["name"] == "TestExport"
            assert data["traits"] == ["A"]
        finally:
            os.unlink(path)

    def test_export_profile_not_found(self):
        loader = PersonalityLoader()
        result = loader.export_profile("missing", "/tmp/out.json")
        assert result is False

    def test_create_miku_default(self):
        loader = PersonalityLoader()
        config = loader.create_miku_default()
        assert config.name == "Hatsune Miku"
        assert "Miku" in loader.profiles
        assert loader.active_profile == config
        assert "Optimistic" in config.traits
        assert config.energy_level == 0.75

    def test_create_miku_default_does_not_override_active(self):
        loader = PersonalityLoader()
        existing = PersonalityConfig(name="Existing", archetype="T")
        loader.active_profile = existing
        loader.create_miku_default()
        assert loader.active_profile == existing
