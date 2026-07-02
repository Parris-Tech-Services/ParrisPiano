from pathlib import Path

from cvp_tutor.settings_store import SettingsStore


def test_settings_store_persists_track_preferences(tmp_path: Path):
    settings_path = tmp_path / "user_settings.json"
    midi_path = str(tmp_path / "example.mid")

    store = SettingsStore(settings_path)
    store.set_track_preferences(midi_path, {"muted_tracks": [1, 3], "solo_tracks": [2]})

    reloaded = SettingsStore(settings_path)
    assert reloaded.get_track_preferences(midi_path) == {"muted_tracks": [1, 3], "solo_tracks": [2]}


def test_settings_store_returns_empty_preferences_for_unknown_file(tmp_path: Path):
    store = SettingsStore(tmp_path / "user_settings.json")
    assert store.get_track_preferences(str(tmp_path / "missing.mid")) == {}
