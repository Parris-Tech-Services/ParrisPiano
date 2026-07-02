from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List
from pathlib import Path

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

    def export_midi(self, path: Path, tempo_us: int = 500_000) -> None:
        """Export captured performance to a MIDI file."""
        if not self.events:
            return
        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("set_tempo", tempo=tempo_us, time=0))

        # Convert seconds to ticks using the fixed tempo (default 120 BPM)
        ticks_per_sec = mid.ticks_per_beat * (1_000_000 / tempo_us)
        last_ts = 0.0
        for ev in sorted(self.events, key=lambda e: e.timestamp):
            delta_sec = ev.timestamp - last_ts
            delta_ticks = int(round(delta_sec * ticks_per_sec))
            msg = ev.message.copy(time=delta_ticks)
            track.append(msg)
            last_ts = ev.timestamp

        mid.save(path)
