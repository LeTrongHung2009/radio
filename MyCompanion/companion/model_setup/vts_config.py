"""
VTS Config - Booth #4711410 Model Setup

Hardcoded handshake parameters, tracking keys, parameter bindings,
and expression configurations specific to the Booth #4711410
half-body Live2D model.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================
# MODEL METADATA (IMMUTABLE)
# ============================================================

MODEL_SOURCE_URL = "https://booth.pm/en/items/4711410"
MODEL_TYPE = "Half-Body Live2D"
ART_CREDIT = "@koahri1"
RIGGER_CREDIT = "@MedL2D"


# ============================================================
# VTube Studio Plugin Handshake Config
# ============================================================

PLUGIN_NAME = "MyCompanion"
PLUGIN_DEVELOPER = "MyCompanion Project"
PLUGIN_ICON = ""  # base64 PNG icon (optional)


@dataclass(frozen=True)
class VTSHandshakeConfig:
    """Immutable handshake configuration for VTube Studio API."""

    plugin_name: str = PLUGIN_NAME
    plugin_developer: str = PLUGIN_DEVELOPER
    api_name: str = "VTubeStudioPublicAPI"
    api_version: str = "1.0"


# ============================================================
# Tracking Parameter Bindings
# ============================================================

@dataclass(frozen=True)
class TrackingParam:
    """A single Live2D tracking parameter binding."""

    param_id: str
    min_value: float = -30.0
    max_value: float = 30.0
    default_value: float = 0.0
    weight: float = 1.0


# Standard parameters for the Booth #4711410 model
TRACKING_PARAMS: dict[str, TrackingParam] = {
    # Face angle
    "face_angle_x": TrackingParam("ParamAngleX", -30.0, 30.0, 0.0),
    "face_angle_y": TrackingParam("ParamAngleY", -30.0, 30.0, 0.0),
    "face_angle_z": TrackingParam("ParamAngleZ", -30.0, 30.0, 0.0),
    # Body
    "body_angle_x": TrackingParam("ParamBodyAngleX", -10.0, 10.0, 0.0),
    "body_angle_y": TrackingParam("ParamBodyAngleY", -10.0, 10.0, 0.0),
    "body_angle_z": TrackingParam("ParamBodyAngleZ", -10.0, 10.0, 0.0),
    # Eyes
    "eye_open_l": TrackingParam("ParamEyeLOpen", 0.0, 1.0, 1.0),
    "eye_open_r": TrackingParam("ParamEyeROpen", 0.0, 1.0, 1.0),
    "eye_smile_l": TrackingParam("ParamEyeLSmile", 0.0, 1.0, 0.0),
    "eye_smile_r": TrackingParam("ParamEyeRSmile", 0.0, 1.0, 0.0),
    "eye_ball_x": TrackingParam("ParamEyeBallX", -1.0, 1.0, 0.0),
    "eye_ball_y": TrackingParam("ParamEyeBallY", -1.0, 1.0, 0.0),
    # Brows
    "brow_l_y": TrackingParam("ParamBrowLY", -1.0, 1.0, 0.0),
    "brow_r_y": TrackingParam("ParamBrowRY", -1.0, 1.0, 0.0),
    "brow_l_form": TrackingParam("ParamBrowLForm", -1.0, 1.0, 0.0),
    "brow_r_form": TrackingParam("ParamBrowRForm", -1.0, 1.0, 0.0),
    # Mouth
    "mouth_form": TrackingParam("ParamMouthForm", -1.0, 1.0, 0.0),
    "mouth_open": TrackingParam("ParamMouthOpenY", 0.0, 1.0, 0.0),
    # Cheek
    "cheek": TrackingParam("ParamCheek", 0.0, 1.0, 0.0),
}


# ============================================================
# Expression / Hotkey IDs
# ============================================================

@dataclass(frozen=True)
class ExpressionConfig:
    """Maps internal emotion names to VTS hotkey IDs."""

    name: str
    hotkey_id: str = ""
    description: str = ""


EXPRESSION_HOTKEYS: dict[str, ExpressionConfig] = {
    "neutral": ExpressionConfig("neutral", "", "Default expression"),
    "happy": ExpressionConfig("happy", "expression_happy", "Happy/smile"),
    "sad": ExpressionConfig("sad", "expression_sad", "Sad/tearful"),
    "angry": ExpressionConfig("angry", "expression_angry", "Angry/frustrated"),
    "surprised": ExpressionConfig("surprised", "expression_surprised", "Surprised/shocked"),
    "embarrassed": ExpressionConfig("embarrassed", "expression_embarrassed", "Blushing"),
}


# ============================================================
# Default Idle Animation Config
# ============================================================

@dataclass(frozen=True)
class IdleAnimConfig:
    """Parameters for idle breathing / micro-movement animation."""

    breath_param: str = "ParamBreath"
    breath_speed: float = 3.0  # seconds per cycle
    breath_amplitude: float = 0.3
    eye_blink_interval_min: float = 2.0
    eye_blink_interval_max: float = 6.0
    eye_blink_duration: float = 0.15


IDLE_ANIM = IdleAnimConfig()


def get_full_config() -> dict:
    """Return the complete model configuration as a dictionary."""
    return {
        "model": {
            "source": MODEL_SOURCE_URL,
            "type": MODEL_TYPE,
            "art_credit": ART_CREDIT,
            "rigger_credit": RIGGER_CREDIT,
        },
        "handshake": {
            "plugin_name": PLUGIN_NAME,
            "plugin_developer": PLUGIN_DEVELOPER,
        },
        "tracking_params": {
            k: {"id": v.param_id, "min": v.min_value, "max": v.max_value, "default": v.default_value}
            for k, v in TRACKING_PARAMS.items()
        },
        "expressions": {
            k: {"hotkey_id": v.hotkey_id, "description": v.description}
            for k, v in EXPRESSION_HOTKEYS.items()
        },
        "idle_anim": {
            "breath_speed": IDLE_ANIM.breath_speed,
            "breath_amplitude": IDLE_ANIM.breath_amplitude,
            "blink_interval": f"{IDLE_ANIM.eye_blink_interval_min}-{IDLE_ANIM.eye_blink_interval_max}s",
        },
    }
