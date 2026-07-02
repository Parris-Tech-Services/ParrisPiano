import mido

from cvp_tutor.performance import PerformanceEvent
from cvp_tutor.scoring import score_performance
from cvp_tutor.timeline import ExpectedMoment


def test_score_requires_all_expected_notes():
    expected = [ExpectedMoment(time=1.0, notes={60, 64}, track_index=0, channel=0)]
    played = [PerformanceEvent(timestamp=1.01, message=mido.Message("note_on", note=60, velocity=90, channel=0))]

    results = score_performance(expected, played)

    assert results[0].verdict == "MISS"
    assert results[0].played == {60}
    assert results[0].matched == {60}


def test_score_marks_extra_notes_as_good_not_perfect():
    expected = [ExpectedMoment(time=1.0, notes={60}, track_index=0, channel=0)]
    played = [
        PerformanceEvent(timestamp=1.0, message=mido.Message("note_on", note=60, velocity=90, channel=0)),
        PerformanceEvent(timestamp=1.02, message=mido.Message("note_on", note=67, velocity=90, channel=0)),
    ]

    results = score_performance(expected, played)

    assert results[0].verdict == "GOOD"
    assert results[0].played == {60, 67}
    assert results[0].matched == {60}
