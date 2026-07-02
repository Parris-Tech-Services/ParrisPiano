from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class MidiPart:
    name: str
    channel: Optional[int]
    track_index: int
    note_count: int
    muted: bool = False
    solo: bool = False


@dataclass
class MidiEvent:
    time: float  # seconds, absolute from song start
    message: "mido.Message"
    track_index: int
    channel: Optional[int]


@dataclass
class ExpectedChord:
    time: float
    notes: Set[int] = field(default_factory=set)
    track_index: int = 0
    channel: Optional[int] = None

