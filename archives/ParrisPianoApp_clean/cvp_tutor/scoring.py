from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple

from .timeline import ExpectedMoment
from .performance import PerformanceEvent


@dataclass
class ScoreEvent:
    expected: Set[int]
    played: Set[int]
    delta_ms: float
    verdict: str  # PERFECT/GOOD/MISS


def score_performance(
    expected: Iterable[ExpectedMoment],
    played: Iterable[PerformanceEvent],
    perfect_ms: int = 50,
    good_ms: int = 110,
) -> List[ScoreEvent]:
    """Match expected chords to played events by time proximity."""
    played_notes: List[Tuple[float, int]] = [
        (ev.timestamp, ev.message.note)
        for ev in played
        if hasattr(ev.message, "note") and getattr(ev.message, "velocity", 0) > 0
    ]
    played_notes.sort(key=lambda t: t[0])

    results: List[ScoreEvent] = []
    pi = 0
    for moment in expected:
        expected_set = moment.notes
        # find notes within window
        window = good_ms / 1000.0
        collected: Set[int] = set()
        while pi < len(played_notes) and played_notes[pi][0] < moment.time - window:
            pi += 1
        probe = pi
        while probe < len(played_notes) and played_notes[probe][0] <= moment.time + window:
            collected.add(played_notes[probe][1])
            probe += 1
        delta = 0.0
        verdict = "MISS"
        if collected:
            # crude timing: take closest note timing difference
            closest = min(collected, key=lambda n: min(abs(moment.time - t[0]) for t in played_notes if t[1] == n))
            closest_time = min(abs(moment.time - t[0]) for t in played_notes if t[1] == closest)
            delta = closest_time * 1000.0
            if delta <= perfect_ms:
                verdict = "PERFECT"
            elif delta <= good_ms:
                verdict = "GOOD"
            else:
                verdict = "MISS"
        results.append(ScoreEvent(expected=expected_set, played=collected, delta_ms=delta, verdict=verdict))
    return results
