from pathlib import Path
import mido
from cvp_tutor import midi_parse


def test_load_midi_basic(tmp_path: Path):
    # create a tiny midi
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("note_on", note=60, velocity=64, time=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=240))
    midi_path = tmp_path / "test.mid"
    mid.save(midi_path)

    parts, events, total = midi_parse.parse_midi(midi_path)
    assert len(parts) == 1
    assert len(events) == 2
    assert total > 0
