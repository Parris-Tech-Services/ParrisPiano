from pathlib import Path

import mido

from cvp_tutor import midi_parse


def test_first_playable_track_can_be_found_after_empty_meta_track(tmp_path: Path):
    mid = mido.MidiFile()

    meta_track = mido.MidiTrack()
    meta_track.append(mido.MetaMessage("track_name", name="Song Title", time=0))
    meta_track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
    mid.tracks.append(meta_track)

    note_track = mido.MidiTrack()
    note_track.append(mido.MetaMessage("track_name", name="Melody", time=0))
    note_track.append(mido.Message("note_on", note=60, velocity=64, time=0, channel=0))
    note_track.append(mido.Message("note_off", note=60, velocity=0, time=240, channel=0))
    mid.tracks.append(note_track)

    midi_path = tmp_path / "meta_first.mid"
    mid.save(midi_path)

    parts, _, _ = midi_parse.parse_midi(midi_path)
    default_index = next((idx for idx, part in enumerate(parts) if part.note_count > 0), 0)

    assert parts[0].note_count == 0
    assert parts[1].note_count > 0
    assert default_index == 1
