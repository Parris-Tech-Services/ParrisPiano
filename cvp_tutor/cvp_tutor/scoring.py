from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple

from .timeline import ExpectedMoment
from .performance import PerformanceEvent


@dataclass
class ScoreEvent:
    expected: Set[int]
    played: Set[int]
    matched_notes: Set[int]  # Notes that were correctly played
    extra_notes: Set[int]  # Wrong notes that were played
    missing_notes: Set[int]  # Expected notes that weren't played
    delta_ms: float  # Average timing offset (positive = late, negative = early)
    verdict: str  # PERFECT/GOOD/LATE/EARLY/MISS/WRONG
    chord_complete: bool  # Whether all expected notes were played
    timing_error_ms: float  # Closest note timing error


def score_performance(
    expected: Iterable[ExpectedMoment],
    played: Iterable[PerformanceEvent],
    perfect_ms: int = 50,
    good_ms: int = 110,
) -> List[ScoreEvent]:
    """Match expected chords to played events by time proximity with enhanced error detection."""
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
        # Find notes within window (extend window slightly for better matching)
        window = good_ms / 1000.0
        collected: Set[int] = set()
        collected_with_timing: List[Tuple[int, float]] = []  # (note, timing_offset_ms)
        
        # Skip notes that are too early
        while pi < len(played_notes) and played_notes[pi][0] < moment.time - window:
            pi += 1
        probe = pi
        
        # Collect all notes within the timing window
        while probe < len(played_notes) and played_notes[probe][0] <= moment.time + window:
            note = played_notes[probe][1]
            timing_offset_ms = (played_notes[probe][0] - moment.time) * 1000.0
            collected.add(note)
            collected_with_timing.append((note, timing_offset_ms))
            probe += 1
        
        # Calculate matched, missing, and extra notes
        matched_notes = expected_set & collected
        missing_notes = expected_set - collected
        extra_notes = collected - expected_set
        chord_complete = len(missing_notes) == 0
        
        # Calculate timing metrics
        delta_ms = 0.0
        timing_error_ms = 0.0
        verdict = "MISS"
        
        if matched_notes:
            # Calculate average timing offset for matched notes
            matched_timings = [t for n, t in collected_with_timing if n in matched_notes]
            if matched_timings:
                delta_ms = sum(matched_timings) / len(matched_timings)
                timing_error_ms = min(abs(t) for t in matched_timings)
                
                # Determine verdict based on timing and completeness
                if chord_complete and len(extra_notes) == 0:
                    if abs(delta_ms) <= perfect_ms:
                        verdict = "PERFECT"
                    elif abs(delta_ms) <= good_ms:
                        verdict = "GOOD"
                    elif delta_ms > 0:
                        verdict = "LATE"
                    else:
                        verdict = "EARLY"
                elif len(extra_notes) > 0:
                    verdict = "WRONG"
                elif len(matched_notes) > 0:
                    # Partial match
                    if abs(delta_ms) <= good_ms:
                        verdict = "GOOD"  # Good timing but incomplete
                    else:
                        verdict = "MISS"  # Incomplete and wrong timing
        elif len(extra_notes) > 0:
            # Only wrong notes, no correct ones
            verdict = "WRONG"
            # Use timing of first extra note for reference
            if collected_with_timing:
                delta_ms = collected_with_timing[0][1]
                timing_error_ms = abs(delta_ms)
        
        results.append(ScoreEvent(
            expected=expected_set,
            played=collected,
            matched_notes=matched_notes,
            extra_notes=extra_notes,
            missing_notes=missing_notes,
            delta_ms=delta_ms,
            verdict=verdict,
            chord_complete=chord_complete,
            timing_error_ms=timing_error_ms
        ))
    return results
