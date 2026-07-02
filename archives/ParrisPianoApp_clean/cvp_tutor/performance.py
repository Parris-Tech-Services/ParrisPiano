from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List

import mido

from .midi_io import MidiIO


@dataclass
class PerformanceEvent:
    timestamp: float
    message: mido.Message


class PerformanceCapture:
    """Capture incoming performance events with timestamps."""

    def __init__(self, midi: MidiIO) -> None:
        self.midi = midi
        self.events: List[PerformanceEvent] = []
        self.start_time = time.perf_counter()
        self.midi.register_listener(self._on_msg)

    def reset(self) -> None:
        self.events.clear()
        self.start_time = time.perf_counter()

    def _on_msg(self, msg: mido.Message) -> None:
        now = time.perf_counter() - self.start_time
        self.events.append(PerformanceEvent(timestamp=now, message=msg))

