from cvp_tutor.playback import track_is_playable


def test_track_is_playable_blocks_muted_tracks_when_no_solo():
    assert track_is_playable(2, {2}, set()) is False
    assert track_is_playable(3, {2}, set()) is True


def test_track_is_playable_prefers_solo_tracks():
    assert track_is_playable(2, {2}, {3}) is False
    assert track_is_playable(3, {2}, {3}) is True
