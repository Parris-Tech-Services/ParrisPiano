import mido

from cvp_tutor.playback import track_is_playable
from cvp_tutor.timeline import group_expected
from cvp_tutor.models import MidiEvent


def test_learning_part_still_produces_expected_chords_even_if_track_is_muted():
    events = [
        MidiEvent(time=0.0, message=mido.Message("note_on", note=60, velocity=90, channel=0), track_index=1, channel=0),
        MidiEvent(time=0.5, message=mido.Message("note_on", note=64, velocity=90, channel=0), track_index=1, channel=0),
    ]

    chords = group_expected(events, learning_channel=0, learning_track=1)

    assert len(chords) == 2
    assert track_is_playable(1, {1}, set()) is False
    assert chords[0].notes == {60}
