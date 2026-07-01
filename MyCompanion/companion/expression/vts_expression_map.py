"""
VTS Expression Map

Maps the 3-Tier emotional states from EmotionMatrix directly to
Live2D parameter IDs for the Booth #4711410 model.

Emotional state -> { paramId: value } mapping.
"""

import logging
from typing import Optional

from companion.expression.vts_connector import VTSConnector
from companion.persona.emotion_matrix import EmotionSnapshot

logger = logging.getLogger(__name__)

# Live2D parameter IDs for the Booth #4711410 half-body model
# These are standard VTube Studio parameter names
PARAM_MOUTH_OPEN = "ParamMouthOpenY"
PARAM_MOUTH_FORM = "ParamMouthForm"  # -1 = frown, +1 = smile
PARAM_EYE_OPEN_L = "ParamEyeLOpen"
PARAM_EYE_OPEN_R = "ParamEyeROpen"
PARAM_EYE_SMILE_L = "ParamEyeLSmile"
PARAM_EYE_SMILE_R = "ParamEyeRSmile"
PARAM_BROW_L_Y = "ParamBrowLY"
PARAM_BROW_R_Y = "ParamBrowRY"
PARAM_BROW_L_FORM = "ParamBrowLForm"
PARAM_BROW_R_FORM = "ParamBrowRForm"
PARAM_BODY_ANGLE_X = "ParamBodyAngleX"
PARAM_BODY_ANGLE_Y = "ParamBodyAngleY"
PARAM_BODY_ANGLE_Z = "ParamBodyAngleZ"
PARAM_CHEEK = "ParamCheek"
PARAM_FACE_ANGLE_X = "ParamAngleX"
PARAM_FACE_ANGLE_Y = "ParamAngleY"
PARAM_FACE_ANGLE_Z = "ParamAngleZ"

# Emotion -> Live2D parameter value presets
_EXPRESSION_PRESETS: dict[str, dict[str, float]] = {
    "neutral": {
        PARAM_MOUTH_FORM: 0.0,
        PARAM_EYE_OPEN_L: 1.0,
        PARAM_EYE_OPEN_R: 1.0,
        PARAM_EYE_SMILE_L: 0.0,
        PARAM_EYE_SMILE_R: 0.0,
        PARAM_BROW_L_Y: 0.0,
        PARAM_BROW_R_Y: 0.0,
        PARAM_CHEEK: 0.0,
    },
    "happy": {
        PARAM_MOUTH_FORM: 0.8,
        PARAM_EYE_OPEN_L: 0.8,
        PARAM_EYE_OPEN_R: 0.8,
        PARAM_EYE_SMILE_L: 0.7,
        PARAM_EYE_SMILE_R: 0.7,
        PARAM_BROW_L_Y: 0.3,
        PARAM_BROW_R_Y: 0.3,
        PARAM_CHEEK: 0.5,
    },
    "sad": {
        PARAM_MOUTH_FORM: -0.6,
        PARAM_EYE_OPEN_L: 0.6,
        PARAM_EYE_OPEN_R: 0.6,
        PARAM_EYE_SMILE_L: 0.0,
        PARAM_EYE_SMILE_R: 0.0,
        PARAM_BROW_L_Y: -0.5,
        PARAM_BROW_R_Y: -0.5,
        PARAM_CHEEK: 0.0,
    },
    "angry": {
        PARAM_MOUTH_FORM: -0.4,
        PARAM_EYE_OPEN_L: 1.0,
        PARAM_EYE_OPEN_R: 1.0,
        PARAM_EYE_SMILE_L: 0.0,
        PARAM_EYE_SMILE_R: 0.0,
        PARAM_BROW_L_Y: -0.7,
        PARAM_BROW_R_Y: -0.7,
        PARAM_BROW_L_FORM: -0.5,
        PARAM_BROW_R_FORM: -0.5,
        PARAM_CHEEK: 0.0,
    },
    "excited": {
        PARAM_MOUTH_FORM: 1.0,
        PARAM_MOUTH_OPEN: 0.6,
        PARAM_EYE_OPEN_L: 1.0,
        PARAM_EYE_OPEN_R: 1.0,
        PARAM_EYE_SMILE_L: 0.5,
        PARAM_EYE_SMILE_R: 0.5,
        PARAM_BROW_L_Y: 0.6,
        PARAM_BROW_R_Y: 0.6,
        PARAM_CHEEK: 0.7,
    },
    "curious": {
        PARAM_MOUTH_FORM: 0.2,
        PARAM_EYE_OPEN_L: 1.0,
        PARAM_EYE_OPEN_R: 1.0,
        PARAM_BROW_L_Y: 0.5,
        PARAM_BROW_R_Y: 0.2,
        PARAM_FACE_ANGLE_Z: 5.0,
        PARAM_CHEEK: 0.0,
    },
    "concerned": {
        PARAM_MOUTH_FORM: -0.3,
        PARAM_EYE_OPEN_L: 0.9,
        PARAM_EYE_OPEN_R: 0.9,
        PARAM_BROW_L_Y: -0.3,
        PARAM_BROW_R_Y: -0.3,
        PARAM_CHEEK: 0.0,
    },
    "playful": {
        PARAM_MOUTH_FORM: 0.6,
        PARAM_EYE_OPEN_L: 0.7,
        PARAM_EYE_OPEN_R: 1.0,
        PARAM_EYE_SMILE_L: 0.8,
        PARAM_EYE_SMILE_R: 0.3,
        PARAM_BROW_L_Y: 0.4,
        PARAM_BROW_R_Y: 0.0,
        PARAM_FACE_ANGLE_Z: -8.0,
        PARAM_CHEEK: 0.4,
    },
    "thoughtful": {
        PARAM_MOUTH_FORM: 0.0,
        PARAM_EYE_OPEN_L: 0.7,
        PARAM_EYE_OPEN_R: 0.7,
        PARAM_BROW_L_Y: 0.2,
        PARAM_BROW_R_Y: 0.2,
        PARAM_FACE_ANGLE_Y: -5.0,
        PARAM_CHEEK: 0.0,
    },
    "surprised": {
        PARAM_MOUTH_FORM: 0.0,
        PARAM_MOUTH_OPEN: 0.8,
        PARAM_EYE_OPEN_L: 1.0,
        PARAM_EYE_OPEN_R: 1.0,
        PARAM_BROW_L_Y: 0.8,
        PARAM_BROW_R_Y: 0.8,
        PARAM_CHEEK: 0.0,
    },
    "bored": {
        PARAM_MOUTH_FORM: -0.1,
        PARAM_EYE_OPEN_L: 0.4,
        PARAM_EYE_OPEN_R: 0.4,
        PARAM_EYE_SMILE_L: 0.0,
        PARAM_EYE_SMILE_R: 0.0,
        PARAM_BROW_L_Y: -0.2,
        PARAM_BROW_R_Y: -0.2,
        PARAM_FACE_ANGLE_Y: 8.0,
        PARAM_CHEEK: 0.0,
    },
    "smug": {
        PARAM_MOUTH_FORM: 0.5,
        PARAM_EYE_OPEN_L: 0.6,
        PARAM_EYE_OPEN_R: 0.9,
        PARAM_EYE_SMILE_L: 0.6,
        PARAM_EYE_SMILE_R: 0.3,
        PARAM_BROW_L_Y: 0.4,
        PARAM_BROW_R_Y: -0.1,
        PARAM_CHEEK: 0.3,
    },
    "embarrassed": {
        PARAM_MOUTH_FORM: -0.2,
        PARAM_EYE_OPEN_L: 0.5,
        PARAM_EYE_OPEN_R: 0.5,
        PARAM_EYE_SMILE_L: 0.3,
        PARAM_EYE_SMILE_R: 0.3,
        PARAM_BROW_L_Y: -0.2,
        PARAM_BROW_R_Y: -0.2,
        PARAM_CHEEK: 1.0,
    },
}


def interpolate_params(
    current: dict[str, float],
    target: dict[str, float],
    factor: float = 0.3,
) -> dict[str, float]:
    """Smooth interpolation between current and target parameter sets."""
    result: dict[str, float] = {}
    all_keys = set(current) | set(target)
    for k in all_keys:
        c = current.get(k, 0.0)
        t = target.get(k, 0.0)
        result[k] = c + (t - c) * factor
    return result


class ExpressionController:
    """
    Translates EmotionSnapshot into VTS parameter injections.

    Smoothly interpolates between expression presets to avoid
    jarring transitions on the Live2D model.
    """

    LERP_FACTOR = 0.3  # per-frame interpolation speed

    def __init__(self, vts: VTSConnector) -> None:
        self._vts = vts
        self._current_params: dict[str, float] = {}
        self._last_emotion = "neutral"

    async def apply_emotion(self, snapshot: EmotionSnapshot) -> None:
        emotion = snapshot.dominant_emotion
        target = _EXPRESSION_PRESETS.get(emotion, _EXPRESSION_PRESETS["neutral"]).copy()

        # Scale by reflex intensity for instantaneous reactions
        if snapshot.reflex_intensity > 0.3:
            reflex_preset = _EXPRESSION_PRESETS.get(
                snapshot.reflex_emotion, {}
            )
            for k, v in reflex_preset.items():
                target[k] = target.get(k, 0.0) * (1 - snapshot.reflex_intensity) + v * snapshot.reflex_intensity

        smoothed = interpolate_params(self._current_params, target, self.LERP_FACTOR)
        self._current_params = smoothed
        self._last_emotion = emotion

        try:
            await self._vts.set_parameters(smoothed)
        except Exception:
            logger.exception("Failed to set VTS expression")

    async def apply_lip_sync(self, amplitude: float) -> None:
        """Map audio amplitude to mouth opening for lip sync."""
        mouth_open = min(1.0, max(0.0, amplitude * 2.0))
        try:
            await self._vts.set_parameter(PARAM_MOUTH_OPEN, mouth_open)
        except Exception:
            logger.exception("Failed to set lip sync parameter")

    async def reset(self) -> None:
        self._current_params = _EXPRESSION_PRESETS["neutral"].copy()
        try:
            await self._vts.set_parameters(self._current_params)
        except Exception:
            pass

    @property
    def stats(self) -> dict:
        return {
            "current_emotion": self._last_emotion,
            "param_count": len(self._current_params),
            "vts": self._vts.stats,
        }
