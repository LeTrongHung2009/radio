"""Tests for MyCompanion/companion/persona/emotion_engine.py"""

import importlib.util
import sys
import os
import time

_mod_path = os.path.join(
    os.path.dirname(__file__), '..', 'MyCompanion', 'companion', 'persona', 'emotion_engine.py'
)
_spec = importlib.util.spec_from_file_location("emotion_engine", _mod_path)
emotion_engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(emotion_engine)

BasicEmotion = emotion_engine.BasicEmotion
BasicEmotionState = emotion_engine.BasicEmotionState
ComplexEmotion = emotion_engine.ComplexEmotion
ComplexEmotionState = emotion_engine.ComplexEmotionState
EQTrait = emotion_engine.EQTrait
EQProfile = emotion_engine.EQProfile
EmotionTrigger = emotion_engine.EmotionTrigger
EmotionSnapshot = emotion_engine.EmotionSnapshot
DEFAULT_TRIGGERS = emotion_engine.DEFAULT_TRIGGERS
DEFAULT_COMPLEX_EMOTIONS = emotion_engine.DEFAULT_COMPLEX_EMOTIONS


class TestBasicEmotion:
    def test_all_emotions_exist(self):
        expected = ["JOY", "SADNESS", "ANGER", "FEAR", "TRUST",
                     "DISGUST", "SURPRISE", "ANTICIPATION"]
        for name in expected:
            assert hasattr(BasicEmotion, name)

    def test_count(self):
        assert len(BasicEmotion) == 8


class TestBasicEmotionState:
    def test_default_values(self):
        state = BasicEmotionState()
        assert state.intensity == 0.0
        assert state.trigger_count == 0
        assert state.last_triggered is None
        assert state.decay_rate == 0.95

    def test_decay(self):
        state = BasicEmotionState(intensity=1.0)
        state.decay()
        assert state.intensity == 0.95

    def test_decay_custom_rate(self):
        state = BasicEmotionState(intensity=1.0)
        state.decay(rate=0.5)
        assert state.intensity == 0.5

    def test_decay_clears_small_values(self):
        state = BasicEmotionState(intensity=0.005)
        state.decay()
        assert state.intensity == 0.0

    def test_trigger(self):
        state = BasicEmotionState()
        state.trigger(0.5)
        assert state.intensity == 0.5
        assert state.trigger_count == 1
        assert state.last_triggered is not None

    def test_trigger_stacks(self):
        state = BasicEmotionState()
        state.trigger(0.3)
        state.trigger(0.3)
        assert state.intensity == 0.6
        assert state.trigger_count == 2

    def test_trigger_capped_at_one(self):
        state = BasicEmotionState()
        state.trigger(0.8)
        state.trigger(0.8)
        assert state.intensity == 1.0

    def test_to_dict(self):
        state = BasicEmotionState(intensity=0.5, trigger_count=3)
        d = state.to_dict()
        assert d["intensity"] == 0.5
        assert d["trigger_count"] == 3
        assert "last_triggered" in d


class TestComplexEmotionState:
    def test_default_values(self):
        state = ComplexEmotionState(
            components={BasicEmotion.JOY: 0.5, BasicEmotion.TRUST: 0.5}
        )
        assert state.intensity == 0.0
        assert state.threshold == 0.2

    def test_is_active_below_threshold(self):
        state = ComplexEmotionState(
            components={BasicEmotion.JOY: 0.5},
            threshold=0.3,
        )
        state.intensity = 0.1
        assert state.is_active() is False

    def test_is_active_above_threshold(self):
        state = ComplexEmotionState(
            components={BasicEmotion.JOY: 0.5},
            threshold=0.3,
        )
        state.intensity = 0.5
        assert state.is_active() is True

    def test_calculate_intensity_empty_components(self):
        state = ComplexEmotionState(components={})
        basic_states = {BasicEmotion.JOY: BasicEmotionState(intensity=1.0)}
        result = state.calculate_intensity(basic_states)
        assert result == 0.0

    def test_calculate_intensity_basic(self):
        state = ComplexEmotionState(
            components={BasicEmotion.JOY: 0.5, BasicEmotion.TRUST: 0.5}
        )
        basic_states = {
            BasicEmotion.JOY: BasicEmotionState(intensity=0.8),
            BasicEmotion.TRUST: BasicEmotionState(intensity=0.6),
        }
        result = state.calculate_intensity(basic_states)
        assert 0.6 < result < 0.7

    def test_calculate_intensity_one_zero(self):
        state = ComplexEmotionState(
            components={BasicEmotion.JOY: 0.5, BasicEmotion.TRUST: 0.5}
        )
        basic_states = {
            BasicEmotion.JOY: BasicEmotionState(intensity=1.0),
            BasicEmotion.TRUST: BasicEmotionState(intensity=0.0),
        }
        result = state.calculate_intensity(basic_states)
        assert result < 0.4

    def test_to_dict(self):
        state = ComplexEmotionState(
            components={BasicEmotion.JOY: 1.0},
            threshold=0.25,
        )
        state.intensity = 0.5
        d = state.to_dict()
        assert d["intensity"] == 0.5
        assert d["is_active"] is True
        assert d["threshold"] == 0.25


class TestEQProfile:
    def test_defaults(self):
        eq = EQProfile()
        assert eq.self_awareness == 0.8
        assert eq.emotion_regulation == 0.7
        assert eq.empathy == 0.75
        assert eq.social_skill == 0.7
        assert eq.motivation == 0.6
        assert eq.professionalism_mode is False
        assert eq.intimacy_level == 0.5
        assert eq.energy_level == 0.7

    def test_should_suppress_not_professional(self):
        eq = EQProfile(professionalism_mode=False)
        assert eq.should_suppress_emotion(BasicEmotion.ANGER, 0.9) is False

    def test_should_suppress_professional_negative(self):
        eq = EQProfile(professionalism_mode=True)
        assert eq.should_suppress_emotion(BasicEmotion.ANGER, 0.8) is True
        assert eq.should_suppress_emotion(BasicEmotion.DISGUST, 0.8) is True
        assert eq.should_suppress_emotion(BasicEmotion.FEAR, 0.8) is True

    def test_should_suppress_professional_positive(self):
        eq = EQProfile(professionalism_mode=True)
        assert eq.should_suppress_emotion(BasicEmotion.JOY, 0.8) is False

    def test_should_suppress_professional_low_intensity(self):
        eq = EQProfile(professionalism_mode=True)
        assert eq.should_suppress_emotion(BasicEmotion.ANGER, 0.3) is False

    def test_get_expression_modifier(self):
        eq = EQProfile()
        modifier = eq.get_expression_modifier()
        assert 0.3 <= modifier <= 1.5

    def test_expression_modifier_low_energy(self):
        eq = EQProfile(energy_level=0.1, social_skill=0.5, intimacy_level=0.0)
        modifier = eq.get_expression_modifier()
        assert modifier < 0.5

    def test_expression_modifier_high_everything(self):
        eq = EQProfile(energy_level=1.0, social_skill=1.0, intimacy_level=1.0)
        modifier = eq.get_expression_modifier()
        assert modifier >= 1.0

    def test_to_dict(self):
        eq = EQProfile()
        d = eq.to_dict()
        assert "self_awareness" in d
        assert "professionalism_mode" in d
        assert "intimacy_level" in d


class TestEmotionTrigger:
    def test_can_trigger_first_time(self):
        trigger = EmotionTrigger(
            name="test",
            keywords=["hello"],
            primary_emotion=BasicEmotion.JOY,
            cooldown_seconds=5.0,
        )
        assert trigger.can_trigger() is True

    def test_can_trigger_on_cooldown(self):
        trigger = EmotionTrigger(
            name="test",
            keywords=["hello"],
            primary_emotion=BasicEmotion.JOY,
            cooldown_seconds=5.0,
        )
        trigger.last_triggered = time.time()
        assert trigger.can_trigger() is False

    def test_can_trigger_after_cooldown(self):
        trigger = EmotionTrigger(
            name="test",
            keywords=["hello"],
            primary_emotion=BasicEmotion.JOY,
            cooldown_seconds=0.1,
        )
        trigger.last_triggered = time.time() - 1.0
        assert trigger.can_trigger() is True

    def test_trigger_returns_correct_data(self):
        secondaries = {BasicEmotion.TRUST: 0.3}
        trigger = EmotionTrigger(
            name="test",
            keywords=["hello"],
            primary_emotion=BasicEmotion.JOY,
            secondary_emotions=secondaries,
            intensity_base=0.5,
        )
        primary, intensity, secs = trigger.trigger()
        assert primary == BasicEmotion.JOY
        assert intensity == 0.5
        assert secs == secondaries
        assert trigger.last_triggered is not None


class TestDefaultTriggers:
    def test_triggers_defined(self):
        assert len(DEFAULT_TRIGGERS) > 0

    def test_all_triggers_have_keywords(self):
        for trigger in DEFAULT_TRIGGERS:
            assert len(trigger.keywords) > 0

    def test_all_triggers_have_valid_emotion(self):
        for trigger in DEFAULT_TRIGGERS:
            assert isinstance(trigger.primary_emotion, BasicEmotion)


class TestDefaultComplexEmotions:
    def test_complex_emotions_defined(self):
        assert len(DEFAULT_COMPLEX_EMOTIONS) > 0

    def test_love_components(self):
        love = DEFAULT_COMPLEX_EMOTIONS[ComplexEmotion.LOVE]
        assert BasicEmotion.JOY in love.components
        assert BasicEmotion.TRUST in love.components

    def test_optimism_components(self):
        opt = DEFAULT_COMPLEX_EMOTIONS[ComplexEmotion.OPTIMISM]
        assert BasicEmotion.JOY in opt.components
        assert BasicEmotion.ANTICIPATION in opt.components

    def test_all_complex_have_components(self):
        for emotion, state in DEFAULT_COMPLEX_EMOTIONS.items():
            assert len(state.components) > 0, f"{emotion} has no components"


class TestEmotionSnapshot:
    def test_creation(self):
        snap = EmotionSnapshot(
            timestamp=time.time(),
            basic_emotions={"joy": 0.5, "anger": 0.1},
            complex_emotions={"love": 0.3},
            dominant_basic="joy",
            dominant_complex="love",
            mood_label="joy",
            eq_state={"empathy": 0.75},
        )
        assert snap.dominant_basic == "joy"

    def test_to_dict(self):
        snap = EmotionSnapshot(
            timestamp=1000.0,
            basic_emotions={"joy": 0.5},
            complex_emotions={},
            dominant_basic=None,
            dominant_complex=None,
            mood_label="neutral",
            eq_state={},
        )
        d = snap.to_dict()
        assert d["timestamp"] == 1000.0
        assert d["mood_label"] == "neutral"

    def test_to_json(self):
        snap = EmotionSnapshot(
            timestamp=1000.0,
            basic_emotions={},
            complex_emotions={},
            dominant_basic=None,
            dominant_complex=None,
            mood_label="neutral",
            eq_state={},
        )
        j = snap.to_json()
        assert '"mood_label": "neutral"' in j
