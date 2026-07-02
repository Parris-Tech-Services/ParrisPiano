from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .scoring import ScoreEvent


NOTE_XP = 10
PERFECT_BONUS_XP = 5
GOOD_BONUS_XP = 2


@dataclass(frozen=True)
class SessionProgress:
    notes_hit: int
    perfect_moments: int
    good_moments: int
    miss_moments: int
    xp_earned: int
    total_xp: int
    level: int
    xp_into_level: int
    xp_to_next_level: int


def live_xp_for_notes(note_count: int) -> int:
    return max(0, note_count) * NOTE_XP


def xp_required_for_level(level: int) -> int:
    """Return the total XP required to reach the given level."""
    if level <= 1:
        return 0
    return 100 * (level - 1) * level // 2


def level_for_total_xp(total_xp: int) -> int:
    level = 1
    while total_xp >= xp_required_for_level(level + 1):
        level += 1
    return level


def calculate_session_progress(results: Iterable[ScoreEvent], starting_xp: int = 0) -> SessionProgress:
    notes_hit = 0
    perfect_moments = 0
    good_moments = 0
    miss_moments = 0
    xp_earned = 0

    for result in results:
        matched_count = len(result.matched)
        notes_hit += matched_count
        xp_earned += live_xp_for_notes(matched_count)

        if result.verdict == "PERFECT":
            perfect_moments += 1
            xp_earned += PERFECT_BONUS_XP
        elif result.verdict == "GOOD":
            good_moments += 1
            xp_earned += GOOD_BONUS_XP
        else:
            miss_moments += 1

    total_xp = starting_xp + xp_earned
    level = level_for_total_xp(total_xp)
    level_floor = xp_required_for_level(level)
    next_level_total = xp_required_for_level(level + 1)

    return SessionProgress(
        notes_hit=notes_hit,
        perfect_moments=perfect_moments,
        good_moments=good_moments,
        miss_moments=miss_moments,
        xp_earned=xp_earned,
        total_xp=total_xp,
        level=level,
        xp_into_level=total_xp - level_floor,
        xp_to_next_level=next_level_total - total_xp,
    )
