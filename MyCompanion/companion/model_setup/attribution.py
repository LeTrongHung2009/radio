"""
Model Attribution - Booth #4711410

Strict licensing attribution for the half-body Live2D model.
Dumps explicit license text to stdout or a PyQt6 modal.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_LICENSE_TEXT = """\
================================================================================
                      LIVE2D MODEL LICENSE & ATTRIBUTION
================================================================================

  Model Source:   Booth Item #4711410
                  https://booth.pm/en/items/4711410
  Type:           Half-Body Live2D Model

  Art Credit:     @koahri1
  Live2D Rigger:  @MedL2D

  Usage:          This model is used in compliance with the creator's license
                  terms as published on Booth. This application (MyCompanion)
                  uses the model strictly for local desktop companion purposes.
                  No redistribution of the model files is performed.

  Attribution is embedded in the codebase per the license requirements.
  Please support the original creators by visiting their profiles.

================================================================================
"""


def get_attribution_text() -> str:
    """Return the full attribution text."""
    return _LICENSE_TEXT


def print_attribution() -> None:
    """Dump the explicit license text to stdout."""
    print(_LICENSE_TEXT)


def show_attribution_dialog() -> None:
    """Show the attribution in a PyQt6 modal dialog."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtCore import Qt

        app = QApplication.instance()
        if app is None:
            logger.warning("No QApplication instance; printing to stdout instead")
            print_attribution()
            return

        dialog = QMessageBox()
        dialog.setWindowTitle("Model Attribution - MyCompanion")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setText("Live2D Model License & Attribution")
        dialog.setDetailedText(_LICENSE_TEXT)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.setWindowFlags(
            dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
        dialog.exec()
    except ImportError:
        print_attribution()


# License check flag
_license_acknowledged = False


def check_license() -> bool:
    """Initialize licensing check. Prints attribution on first call."""
    global _license_acknowledged
    if not _license_acknowledged:
        logger.info("Model Attribution (Booth #4711410):")
        logger.info("  Art: @koahri1 | Rigger: @MedL2D")
        logger.info("  Source: https://booth.pm/en/items/4711410")
        _license_acknowledged = True
    return True
