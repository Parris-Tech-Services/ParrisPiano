from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_settings_path() -> Path:
    return Path("logs") / "user_settings.json"


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_settings_path()
        self.data: dict[str, Any] = {"track_preferences": {}, "ui_preferences": {}}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(loaded, dict):
            self.data = {"track_preferences": {}, "ui_preferences": {}, **loaded}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def get_track_preferences(self, midi_path: str) -> dict[str, Any]:
        prefs = self.data.get("track_preferences", {})
        value = prefs.get(midi_path, {})
        return value if isinstance(value, dict) else {}

    def set_track_preferences(self, midi_path: str, preferences: dict[str, Any]) -> None:
        self.data.setdefault("track_preferences", {})[midi_path] = preferences
        self.save()

    def get_ui_preferences(self) -> dict[str, Any]:
        prefs = self.data.get("ui_preferences", {})
        return prefs if isinstance(prefs, dict) else {}

    def set_ui_preferences(self, preferences: dict[str, Any]) -> None:
        self.data["ui_preferences"] = preferences
        self.save()
