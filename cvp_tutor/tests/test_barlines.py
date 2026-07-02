from pathlib import Path

import mido

from cvp_tutor.midi_parse import build_barlines, build_time_signatures


def test_build_barlines_uses_default_four_four_grid(tmp_path: Path):
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
    track.append(mido.Message("note_on", note=60, velocity=64, time=0, channel=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=1920, channel=0))
    track.append(mido.Message("note_on", note=62, velocity=64, time=1920, channel=0))
    track.append(mido.Message("note_off", note=62, velocity=0, time=480, channel=0))
    mid.tracks.append(track)

    midi_path = tmp_path / "bars.mid"
    mid.save(midi_path)

    barlines = build_barlines(midi_path)

    assert barlines[0] == 0.0
    assert round(barlines[1], 3) == 2.0


def test_build_time_signatures_returns_visible_signature_changes(tmp_path: Path):
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
    track.append(mido.Message("note_on", note=60, velocity=64, time=0, channel=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=1920, channel=0))
    track.append(mido.MetaMessage("time_signature", numerator=3, denominator=4, time=0))
    track.append(mido.Message("note_on", note=62, velocity=64, time=1440, channel=0))
    track.append(mido.Message("note_off", note=62, velocity=0, time=480, channel=0))
    mid.tracks.append(track)

    midi_path = tmp_path / "time_signatures.mid"
    mid.save(midi_path)

    signatures = build_time_signatures(midi_path)

    assert signatures[0] == (0.0, 4, 4)
    assert signatures[1][1:] == (3, 4)
    assert round(signatures[1][0], 3) == 2.0
