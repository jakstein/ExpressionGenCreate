"""Path helpers that work both in development and PyInstaller one-file builds."""

from __future__ import annotations

import os
import sys


def _app_dir() -> str:
    """Return the directory containing the running application.

    - Development (python main.py): project root folder.
    - PyInstaller one-file: directory next to the extracted .exe.
    """
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running as normal Python — project root (parent of expressiongen/)
        return os.path.dirname(os.path.dirname(__file__))


def get_presets_dir() -> str:
    """Return the path to the presets/ folder, creating it if missing."""
    d = os.path.join(_app_dir(), "presets")
    os.makedirs(d, exist_ok=True)
    return d


def get_output_base() -> str:
    """Return the default output/ folder path (relative to app dir)."""
    return os.path.join(_app_dir(), "output")
