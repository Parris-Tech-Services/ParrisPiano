from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from .timeline import ExpectedMoment
from .performance import PerformanceEvent


@dataclass
class ScoreEvent:
    expected: Set[int]
    played: Set[int]
    matched: Set[int]
    delta_ms: float
    verdict: str  # PERFECT/GOOD/MISS


def score_performance(
    expected: Iterable[ExpectedMoment],
    played: Iterable[PerformanceEvent],
    perfect_ms: int = 50,
    good_ms: int = 110,
) -> List[ScoreEvent]:
    """Match expected chords to nearby played notes without reusing the same note-on twice."""
    window = good_ms / 1000.0
    note_ons = [
        {"time": event.timestamp, "note": event.message.note, "used": False}
        for event in played
        if hasattr(event.message, "note") and getattr(event.message, "velocity", 0) > 0
    ]
    note_ons.sort(key=lambda item: item["time"])

    results: List[ScoreEvent] = []
    for moment in expected:
        nearby = [
            (index, item)
            for index, item in enumerate(note_ons)
            if not item["used"] and abs(item["time"] - moment.time) <= window
        ]
        nearby_notes = {item["note"] for _, item in nearby}

        matched_indices: list[int] = []
        matched_notes: set[int] = set()
        deltas_ms: list[float] = []
        missing_note = False

        for note in sorted(moment.notes):
            candidates = [
                (index, item)
                for index, item in nearby
                if item["note"] == note and index not in matched_indices
            ]
            if not candidates:
                missing_note = True
                break

            best_index, best_match = min(candidates, key=lambda pair: abs(pair[1]["time"] - moment.time))
            matched_indices.append(best_index)
            matched_notes.add(note)
            deltas_ms.append(abs(best_match["time"] - moment.time) * 1000.0)

        verdict = "MISS"
        delta_ms = 0.0
        if not missing_note and matched_indices:
            for index in matched_indices:
                note_ons[index]["used"] = True
            delta_ms = max(deltas_ms)
            extras = nearby_notes - moment.notes
            if delta_ms <= perfect_ms and not extras:
                verdict = "PERFECT"
            elif delta_ms <= good_ms:
                verdict = "GOOD"

        results.append(
            ScoreEvent(
                expected=moment.notes,
                played=nearby_notes,
                matched=matched_notes,
                delta_ms=delta_ms,
                verdict=verdict,
            )
        )

    return results
