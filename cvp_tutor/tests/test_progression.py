from cvp_tutor.progression import calculate_session_progress, level_for_total_xp, live_xp_for_notes, xp_required_for_level
from cvp_tutor.scoring import ScoreEvent


def test_progression_awards_xp_per_matched_note_and_verdict_bonus():
    results = [
        ScoreEvent(expected={60}, played={60}, matched={60}, delta_ms=10.0, verdict="PERFECT"),
        ScoreEvent(expected={62, 65}, played={62, 65}, matched={62, 65}, delta_ms=75.0, verdict="GOOD"),
        ScoreEvent(expected={67}, played=set(), matched=set(), delta_ms=0.0, verdict="MISS"),
    ]

    progress = calculate_session_progress(results, starting_xp=0)

    assert progress.notes_hit == 3
    assert progress.xp_earned == 37
    assert progress.total_xp == 37
    assert progress.level == 1
    assert progress.xp_to_next_level == 63


def test_progression_levels_up_from_existing_xp():
    results = [
        ScoreEvent(expected={60}, played={60}, matched={60}, delta_ms=5.0, verdict="PERFECT"),
    ]

    progress = calculate_session_progress(results, starting_xp=95)

    assert progress.xp_earned == 15
    assert progress.total_xp == 110
    assert progress.level == 2
    assert progress.xp_into_level == 10
    assert progress.xp_to_next_level == 190


def test_live_xp_awards_immediate_base_note_progress():
    assert live_xp_for_notes(0) == 0
    assert live_xp_for_notes(1) == 10
    assert live_xp_for_notes(3) == 30


def test_level_thresholds_scale_cleanly():
    assert xp_required_for_level(1) == 0
    assert xp_required_for_level(2) == 100
    assert xp_required_for_level(3) == 300
    assert level_for_total_xp(0) == 1
    assert level_for_total_xp(100) == 2
    assert level_for_total_xp(299) == 2
    assert level_for_total_xp(300) == 3
