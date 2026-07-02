from cvp_tutor.ui_main import _format_clock, _playback_meter_text


def test_format_clock_uses_minute_second_display():
    assert _format_clock(0) == "00:00"
    assert _format_clock(65.9) == "01:05"


def test_playback_meter_text_shows_waiting_prompt():
    text = _playback_meter_text(12.0, 100.0, 12.0, True)
    assert "00:12 / 01:40" in text
    assert "play now" in text


def test_playback_meter_text_shows_countdown():
    text = _playback_meter_text(12.0, 100.0, 15.2, False)
    assert "Next cue in 3.2s" in text
