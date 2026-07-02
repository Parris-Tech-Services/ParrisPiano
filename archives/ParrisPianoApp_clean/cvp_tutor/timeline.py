from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from .models import MidiEvent


@dataclass
class ExpectedMoment:
    time: float
    notes: Set[int]
    track_index: int
    channel: int | None


def group_expected(events: Iterable[MidiEvent], learning_channel: int | None, learning_track: int | None, window_ms: int = 40) -> List[ExpectedMoment]:
    """Group nearby note_on events into chord moments."""
    filtered = [
        ev for ev in events
        if ev.message.type == "note_on" and ev.message.velocity > 0
        and (learning_channel is None or ev.channel == learning_channel)
        and (learning_track is None or ev.track_index == learning_track)
    ]
    filtered.sort(key=lambda e: e.time)
    window = window_ms / 1000.0
    moments: List[ExpectedMoment] = []
    for ev in filtered:
        if not moments or (ev.time - moments[-1].time) > window:
            moments.append(ExpectedMoment(time=ev.time, notes={ev.message.note}, track_index=ev.track_index, channel=ev.channel))
        else:
            moments[-1].notes.add(ev.message.note)
    return moments
