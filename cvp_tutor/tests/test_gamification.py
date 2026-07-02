from pathlib import Path
import tempfile

from cvp_tutor.gamification import GamificationManager
from cvp_tutor.scoring import ScoreEvent


def make_event(expected, verdict):
    return ScoreEvent(
        expected=set(expected),
        played=set(expected) if verdict in ("PERFECT", "GOOD") else set(),
        matched_notes=set(expected) if verdict in ("PERFECT", "GOOD") else set(),
        extra_notes=set(),
        missing_notes=set() if verdict in ("PERFECT", "GOOD") else set(expected),
        delta_ms=0.0,
        verdict=verdict,
        chord_complete=(verdict in ("PERFECT", "GOOD")),
        timing_error_ms=0.0,
    )


def test_gamification_simple():
    with tempfile.TemporaryDirectory() as td:
        profile = Path(td) / "hero_profile.json"
        gm = GamificationManager(profile)

        events = [make_event([60], "PERFECT"), make_event([62], "GOOD"), make_event([64], "MISS")]
        reward = gm.apply_score(events)

        assert reward.xp_gained > 0
        assert reward.gold_gained > 0
        # Profile persisted
        loaded = GamificationManager(profile)
        assert loaded.profile.xp >= reward.xp_gained


if __name__ == "__main__":
    test_gamification_simple()
    print("Gamification simulation OK")
