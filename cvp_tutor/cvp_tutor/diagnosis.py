"""Advanced diagnosis engine for piano performance analysis.

This module provides rule-based pattern detection to identify common
piano playing issues and generate actionable feedback.

Example usage:
    from cvp_tutor.diagnosis import diagnose_performance
    from cvp_tutor.scoring import ScoreEvent

    score_events = [ScoreEvent(...), ...]
    insights = diagnose_performance(score_events)
    for insight in insights:
        print(insight.message)
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

from .scoring import ScoreEvent
from .timeline import ExpectedMoment

try:
    import music21 as m21

    HAS_MUSIC21 = True
except ImportError:
    HAS_MUSIC21 = False


def _stream_from_events(events: List[Tuple[int, float]]) -> m21.stream.Stream:
    """Convert a list of (midi_pitch, offset) into a music21 Stream.

    This is intentionally permissive: adapt to your `PerformanceEvent` shape.
    """
    s = m21.stream.Stream()
    for ev in events:
        if not ev:
            continue
        pitch = ev[0]
        try:
            if isinstance(pitch, int):
                n = m21.note.Note(pitch)
            else:
                n = m21.note.Note(str(pitch))
        except Exception:
            # fallback: try creating a Rest for safety
            n = m21.note.Rest()
        s.append(n)
    return s


@dataclass
class DiagnosisInsight:
    """A single diagnostic insight with message and drill suggestion."""
    message: str
    severity: str  # "high", "medium", "low"
    drill_suggestion: str
    affected_bars: List[int]  # Bar numbers where this issue occurs
    metric_value: float  # Numeric value for this metric


def diagnose_performance(
    score_events: List[ScoreEvent],
    expected_moments: Optional[List[ExpectedMoment]] = None,
    bar_duration: float = 2.0,  # Approximate seconds per bar
) -> List[DiagnosisInsight]:
    """Analyze score events and generate diagnostic insights.
    
    Returns a list of insights sorted by severity, with the most critical
    issues first. Typically returns 2-3 top insights.
    """
    if not score_events:
        return []
    
    insights: List[DiagnosisInsight] = []
    
    # 1. Detect consistent timing bias
    timing_bias = _detect_timing_bias(score_events)
    if timing_bias:
        insights.append(timing_bias)
    
    # 2. Detect chord incompleteness patterns
    chord_issues = _detect_chord_incompleteness(score_events)
    if chord_issues:
        insights.append(chord_issues)
    
    # 3. Detect wrong note patterns
    wrong_note_issues = _detect_wrong_notes(score_events)
    if wrong_note_issues:
        insights.append(wrong_note_issues)
    
    # 4. Detect weak fingers/specific notes
    weak_notes = _detect_weak_notes(score_events)
    if weak_notes:
        insights.append(weak_notes)
    
    # 5. Detect rushing after rests (if we have timing info)
    if expected_moments:
        rushing_issues = _detect_rushing_after_rests(score_events, expected_moments)
        if rushing_issues:
            insights.append(rushing_issues)
    
    # Sort by severity and return top 3
    severity_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: (severity_order[x.severity], -abs(x.metric_value)))
    return insights[:3]


def _detect_timing_bias(score_events: List[ScoreEvent]) -> Optional[DiagnosisInsight]:
    """Detect if player is consistently early or late."""
    timing_offsets = [e.delta_ms for e in score_events if e.verdict not in ("MISS", "WRONG")]
    if len(timing_offsets) < 5:
        return None
    
    avg_offset = sum(timing_offsets) / len(timing_offsets)
    abs_avg = abs(avg_offset)
    
    if abs_avg > 50:  # More than 50ms average bias
        hand = "left" if avg_offset > 0 else "right"  # Positive = late
        severity = "high" if abs_avg > 75 else "medium"
        message = f"You're consistently {abs_avg:.0f}ms {'late' if avg_offset > 0 else 'early'}"
        drill = f"Practice with metronome at slower tempo, focus on {hand} hand timing"
        return DiagnosisInsight(
            message=message,
            severity=severity,
            drill_suggestion=drill,
            affected_bars=[],
            metric_value=avg_offset
        )
    return None


def _detect_chord_incompleteness(score_events: List[ScoreEvent]) -> Optional[DiagnosisInsight]:
    """Detect patterns in missing chord notes."""
    incomplete_chords = [e for e in score_events if not e.chord_complete and len(e.expected) > 1]
    if len(incomplete_chords) < 3:
        return None
    
    # Check if there's a pattern in which notes are missing
    missing_patterns = Counter()
    for event in incomplete_chords:
        if event.missing_notes:
            # Check if it's typically the top or bottom note
            sorted_expected = sorted(event.expected)
            sorted_missing = sorted(event.missing_notes)
            if sorted_missing[0] == sorted_expected[0]:
                missing_patterns["bottom"] += 1
            if sorted_missing[-1] == sorted_expected[-1]:
                missing_patterns["top"] += 1
    
    if missing_patterns:
        most_common = missing_patterns.most_common(1)[0]
        pattern, count = most_common
        percentage = (count / len(incomplete_chords)) * 100
        
        if percentage > 60:  # More than 60% of incomplete chords
            severity = "high" if percentage > 80 else "medium"
            message = f"You miss the {pattern} note in {percentage:.0f}% of chords"
            drill = f"Practice chord voicing: focus on {pattern} note, play chords slowly and hold all notes"
            return DiagnosisInsight(
                message=message,
                severity=severity,
                drill_suggestion=drill,
                affected_bars=[],
                metric_value=percentage
            )
    
    # General incompleteness
    incomplete_rate = (len(incomplete_chords) / len(score_events)) * 100
    if incomplete_rate > 30:
        severity = "high" if incomplete_rate > 50 else "medium"
        message = f"{incomplete_rate:.0f}% of chords are incomplete"
        drill = "Practice playing all notes of each chord simultaneously, use slower tempo"
        return DiagnosisInsight(
            message=message,
            severity=severity,
            drill_suggestion=drill,
            affected_bars=[],
            metric_value=incomplete_rate
        )
    
    return None


def _detect_wrong_notes(score_events: List[ScoreEvent]) -> Optional[DiagnosisInsight]:
    """Detect patterns in wrong notes played."""
    wrong_events = [e for e in score_events if e.verdict == "WRONG" or len(e.extra_notes) > 0]
    if len(wrong_events) < 3:
        return None
    
    # Check for common wrong notes
    wrong_note_counts = Counter()
    for event in wrong_events:
        for note in event.extra_notes:
            wrong_note_counts[note] += 1
    
    if wrong_note_counts:
        most_wrong, count = wrong_note_counts.most_common(1)[0]
        wrong_rate = (len(wrong_events) / len(score_events)) * 100
        
        if wrong_rate > 15:  # More than 15% wrong notes
            note_name = _midi_to_note_name(most_wrong)
            severity = "high" if wrong_rate > 25 else "medium"
            message = f"You play wrong notes {wrong_rate:.0f}% of the time (often {note_name})"
            drill = f"Practice note identification: focus on reading ahead, check finger positions"
            return DiagnosisInsight(
                message=message,
                severity=severity,
                drill_suggestion=drill,
                affected_bars=[],
                metric_value=wrong_rate
            )
    
    return None


def _detect_weak_notes(score_events: List[ScoreEvent]) -> Optional[DiagnosisInsight]:
    """Detect specific notes that are frequently missed."""
    missed_notes = Counter()
    total_expected = Counter()
    
    for event in score_events:
        for note in event.expected:
            total_expected[note] += 1
        for note in event.missing_notes:
            missed_notes[note] += 1
    
    # Find notes with high miss rate
    weak_notes = []
    for note in total_expected:
        miss_rate = (missed_notes[note] / total_expected[note]) * 100
        if miss_rate > 40 and total_expected[note] >= 3:  # Missed >40% and appears at least 3 times
            weak_notes.append((note, miss_rate))
    
    if weak_notes:
        weak_notes.sort(key=lambda x: x[1], reverse=True)
        top_weak = weak_notes[0]
        note_name = _midi_to_note_name(top_weak[0])
        severity = "medium" if top_weak[1] > 60 else "low"
        message = f"You frequently miss {note_name} ({top_weak[1]:.0f}% miss rate)"
        drill = f"Practice {note_name} specifically: isolate this note, practice finger positioning"
        return DiagnosisInsight(
            message=message,
            severity=severity,
            drill_suggestion=drill,
            affected_bars=[],
            metric_value=top_weak[1]
        )
    
    return None


def _detect_rushing_after_rests(
    score_events: List[ScoreEvent],
    expected_moments: List[ExpectedMoment]
) -> Optional[DiagnosisInsight]:
    """Detect if player rushes after rests."""
    if len(score_events) < 2 or len(expected_moments) < 2:
        return None
    
    rushing_count = 0
    rest_count = 0
    
    for i in range(1, len(expected_moments)):
        prev_time = expected_moments[i-1].time
        curr_time = expected_moments[i].time
        gap = curr_time - prev_time
        
        # If there's a significant gap (rest), check if next note was rushed
        if gap > 0.3:  # More than 300ms gap (rest)
            rest_count += 1
            if i < len(score_events):
                event = score_events[i]
                # Check if played early (negative delta means early)
                if event.delta_ms < -30:  # More than 30ms early
                    rushing_count += 1
    
    if rest_count > 0:
        rush_rate = (rushing_count / rest_count) * 100
        if rush_rate > 50:  # Rush after rests more than 50% of the time
            severity = "medium" if rush_rate > 70 else "low"
            message = f"You rush {rush_rate:.0f}% of the time after rests"
            drill = "Practice counting rests: count '1-2-3-4' during rests, wait for the beat"
            return DiagnosisInsight(
                message=message,
                severity=severity,
                drill_suggestion=drill,
                affected_bars=[],
                metric_value=rush_rate
            )
    
    return None


def _midi_to_note_name(midi_note: int) -> str:
    """Convert MIDI note to note name."""
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi_note // 12) - 1
    note = note_names[midi_note % 12]
    return f"{note}{octave}"


def analyze_performance(events: List[Tuple[int, float]], max_chords: int = 10) -> Dict[str, Any]:
    """Analyze a short performance event sequence using music21.

    Returns a dictionary with fields like `key` and a short list of detected
    chord names. This is a lightweight starting point for richer diagnosis.
    """
    if not events:
        return {"key": None, "chords": [], "notes": []}
    
    if not HAS_MUSIC21:
        return {"key": None, "chords": [], "notes": []}

    s = _stream_from_events(events)

    # Estimate key
    try:
        k = s.analyze('key')
        key_name = str(k)
    except Exception:
        key_name = None

    # Chordify and collect chord names
    chords = []
    try:
        chordified = s.chordify()
        for c in chordified.recurse().getElementsByClass(m21.chord.Chord):
            name = c.commonName if getattr(c, 'commonName', None) else c.pitchedCommonName if getattr(c, 'pitchedCommonName', None) else c.fullName
            chords.append(name)
            if len(chords) >= max_chords:
                break
    except Exception:
        chords = []

    # Provide raw notes for additional processing
    notes = [n.pitch.midi for n in s.recurse().notes if hasattr(n, 'pitch')]

    return {"key": key_name, "chords": chords, "notes": notes}


__all__ = ["analyze_performance", "diagnose_performance", "DiagnosisInsight"]
