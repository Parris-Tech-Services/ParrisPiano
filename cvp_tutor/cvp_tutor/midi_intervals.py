from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from .models import MidiEvent


def extract_note_intervals(
    events: Iterable[MidiEvent],
    learning_channel: int | None,
    learning_track: int | None,
    show_all: bool = False,
    learning_tracks: set[int] | None = None,
) -> Tuple[List[Tuple[int, float, float]], List[int]]:
    """Pair note_on/note_off into (midi_note, start_sec, duration_sec). Returns intervals and notes seen."""
    note_starts: Dict[Tuple[int, int | None], float] = {}
    notes_seen: List[int] = []
    intervals: List[Tuple[int, float, float]] = []
    for ev in events:
        msg = ev.message
        if msg.type == "note_on" and msg.velocity > 0:
            if not show_all:
                if (learning_channel is not None and msg.channel != learning_channel) or (
                    learning_track is not None and ev.track_index != learning_track
                ) or (learning_tracks is not None and ev.track_index not in learning_tracks):
                    continue
            note_starts[(msg.note, ev.track_index)] = ev.time
            notes_seen.append(msg.note)
        elif msg.type in {"note_off", "note_on"}:
            key = (getattr(msg, "note", -1), ev.track_index)
            if key in note_starts:
                start = note_starts.pop(key)
                end = ev.time
                intervals.append((key[0], start, max(end - start, 0.05)))

    for (note, _), start in note_starts.items():
        intervals.append((note, start, 0.1))

    return intervals, notes_seen
