from cvp_tutor.playback import shift_start_for_pause


def test_shift_start_for_pause_adds_pause_duration():
    assert shift_start_for_pause(10.0, 12.0, 14.5) == 12.5


def test_shift_start_for_pause_ignores_negative_pause():
    assert shift_start_for_pause(10.0, 12.0, 11.0) == 10.0
