"""Preset storage: named JSON files in the ``presets/`` folder."""

from __future__ import annotations

import glob
import json
import os
from typing import List

from .models import Preset
from .paths import get_presets_dir

PRESET_DIR = get_presets_dir()
CURRENT_FILE = os.path.join(PRESET_DIR, "__current__.json")


def ensure_dir() -> None:
    os.makedirs(PRESET_DIR, exist_ok=True)


def list_presets() -> List[str]:
    ensure_dir()
    files = glob.glob(os.path.join(PRESET_DIR, "*.json"))
    names = []
    for f in files:
        base = os.path.splitext(os.path.basename(f))[0]
        if base == "__current__":
            continue
        names.append(base)
    return sorted(names)


def _safe(name: str) -> str:
    return name.replace(os.sep, "_").strip() or "untitled"


def save_preset(preset: Preset, name: str | None = None) -> str:
    ensure_dir()
    name = _safe(name or preset.name or "untitled")
    path = os.path.join(PRESET_DIR, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(preset.to_dict(), f, indent=2, ensure_ascii=False)
    return path


def load_preset(name: str) -> Preset:
    path = os.path.join(PRESET_DIR, _safe(name) + ".json")
    with open(path, encoding="utf-8") as f:
        return Preset.from_dict(json.load(f))


def save_preset_path(preset: Preset, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(preset.to_dict(), f, indent=2, ensure_ascii=False)


def load_preset_path(path: str) -> Preset:
    with open(path, encoding="utf-8") as f:
        return Preset.from_dict(json.load(f))


def save_current(preset: Preset) -> None:
    ensure_dir()
    with open(CURRENT_FILE, "w", encoding="utf-8") as f:
        json.dump(preset.to_dict(), f, indent=2, ensure_ascii=False)


def load_current() -> Preset | None:
    if not os.path.exists(CURRENT_FILE):
        return None
    try:
        with open(CURRENT_FILE, encoding="utf-8") as f:
            return Preset.from_dict(json.load(f))
    except (ValueError, OSError):
        return None
