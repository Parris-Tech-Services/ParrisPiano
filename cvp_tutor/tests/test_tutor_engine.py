from cvp_tutor.tutor_engine import TutorEngine
from cvp_tutor.models import MidiEvent
import mido


def test_build_expected_groups_chords():
    evs = [
        MidiEvent(time=0.0, message=mido.Message("note_on", note=60, velocity=100, channel=0), track_index=0, channel=0),
        MidiEvent(time=0.02, message=mido.Message("note_on", note=64, velocity=100, channel=0), track_index=0, channel=0),
        MidiEvent(time=0.5, message=mido.Message("note_on", note=67, velocity=100, channel=0), track_index=0, channel=0),
    ]
    tutor = TutorEngine(chord_window_ms=40)
    chords = tutor.build_expected(evs, learning_channel=0, learning_track=0)
    assert len(chords) == 2
    assert chords[0].notes == {60, 64}
    assert chords[1].notes == {67}
