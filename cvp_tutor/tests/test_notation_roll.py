import mido

from cvp_tutor.models import MidiEvent
from cvp_tutor.notation_roll import (
    build_rendered_notes,
    build_rests,
    note_staff_position,
    note_y,
    pitch_uses_treble_staff,
)


def test_note_y_moves_higher_notes_up_the_staff():
    middle = note_y(60, 96.0, 12.0)
    upper = note_y(72, 96.0, 12.0)
    lower = note_y(48, 96.0, 12.0)

    assert upper < middle
    assert lower > middle


def test_build_rendered_notes_pairs_note_on_and_off():
    events = [
        MidiEvent(time=0.0, message=mido.Message("note_on", note=60, velocity=64, channel=0), track_index=1, channel=0),
        MidiEvent(time=0.5, message=mido.Message("note_off", note=60, velocity=0, channel=0), track_index=1, channel=0),
        MidiEvent(time=0.75, message=mido.Message("note_on", note=55, velocity=64, channel=0), track_index=1, channel=0),
        MidiEvent(time=1.0, message=mido.Message("note_off", note=55, velocity=0, channel=0), track_index=1, channel=0),
    ]

    rendered = build_rendered_notes(events, learning_channel=0, learning_track=1)

    assert len(rendered) == 2
    assert rendered[0].note == 60
    assert rendered[0].start == 0.0
    assert rendered[0].duration == 0.5
    assert rendered[1].note == 55


def test_build_rests_inserts_gap_for_missing_music():
    events = [
        MidiEvent(time=0.0, message=mido.Message("note_on", note=64, velocity=64, channel=0), track_index=1, channel=0),
        MidiEvent(time=0.25, message=mido.Message("note_off", note=64, velocity=0, channel=0), track_index=1, channel=0),
        MidiEvent(time=1.5, message=mido.Message("note_on", note=67, velocity=64, channel=0), track_index=1, channel=0),
        MidiEvent(time=1.75, message=mido.Message("note_off", note=67, velocity=0, channel=0), track_index=1, channel=0),
    ]

    rendered = build_rendered_notes(events, learning_channel=0, learning_track=1)
    rests = build_rests(rendered, total_time=2.0, treble=True, gap_threshold=0.5)

    assert rests
    assert round(rests[0].start, 2) == 0.25
    assert pitch_uses_treble_staff(rendered[0].note) is True


def test_sharp_notes_share_staff_position_with_their_natural_letter():
    f_natural_pos = note_staff_position(65)
    f_sharp_pos = note_staff_position(66)

    assert f_natural_pos[0] == f_sharp_pos[0]
    assert f_natural_pos[1] == ""
    assert f_sharp_pos[1] == "#"
