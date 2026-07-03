from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

import mido
from loguru import logger

from .midi_io import MidiIO


@dataclass
class PerformanceEvent:
    timestamp: float
    message: mido.Message


class PerformanceCapture:
    """Capture incoming performance events with high-precision timestamps and real-time analysis."""

    def __init__(self, midi: MidiIO) -> None:
        self.midi = midi
        self.events: List[PerformanceEvent] = []
        self.start_time = time.perf_counter()
        self.midi.register_listener(self._on_msg)
        
        # Real-time state tracking
        self.currently_held: Set[int] = set()  # Notes currently being held
        self.recent_events: deque[PerformanceEvent] = deque(maxlen=100)  # Last 100 events for real-time analysis
        self.pedal_state: bool = False  # Sustain pedal state
        
    def reset(self) -> None:
        """Reset all captured events and state."""
        self.events.clear()
        self.currently_held.clear()
        self.recent_events.clear()
        self.pedal_state = False
        self.start_time = time.perf_counter()

    def _on_msg(self, msg: mido.Message) -> None:
        """Handle incoming MIDI message with high-precision timestamping."""
        now = time.perf_counter() - self.start_time
        event = PerformanceEvent(timestamp=now, message=msg)
        self.events.append(event)
        self.recent_events.append(event)
        
        # Track held notes
        if msg.type == "note_on" and msg.velocity > 0:
            self.currently_held.add(msg.note)
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            self.currently_held.discard(msg.note)
        
        # Track pedal state
        if msg.type == "control_change" and msg.control == 64:  # Sustain pedal
            self.pedal_state = msg.value >= 64
        
        logger.debug(f"Performance event: {msg.type} note={getattr(msg, 'note', None)} at {now:.3f}s")

    def get_recent_notes(self, window_seconds: float = 1.0) -> List[PerformanceEvent]:
        """Get notes played in the last N seconds."""
        if not self.recent_events:
            return []
        cutoff = time.perf_counter() - self.start_time - window_seconds
        return [e for e in self.recent_events if e.timestamp >= cutoff]
    
    def get_currently_held(self) -> Set[int]:
        """Get set of notes currently being held."""
        return self.currently_held.copy()
    
    def get_pedal_state(self) -> bool:
        """Get current sustain pedal state."""
        return self.pedal_state
    
    def get_latency_stats(self) -> Optional[dict]:
        """Calculate latency statistics from recent events."""
        if len(self.recent_events) < 2:
            return None
        
        # Calculate time between consecutive events (as a proxy for latency)
        intervals = []
        for i in range(1, len(self.recent_events)):
            interval = self.recent_events[i].timestamp - self.recent_events[i-1].timestamp
            if interval > 0:
                intervals.append(interval)
        
        if not intervals:
            return None
        
        return {
            "min_interval": min(intervals),
            "max_interval": max(intervals),
            "avg_interval": sum(intervals) / len(intervals),
            "event_count": len(self.recent_events)
        }

    def export_midi(self, path: Path, tempo: int = 500000, ticks_per_beat: int = 480) -> None:
        """Export captured performance events to a MIDI file.

        Uses `mido.second2tick` to convert event timestamps to delta ticks and writes
        messages into a single track. Existing message attributes are preserved.
        """
        if not self.events:
            raise ValueError("No performance events to export")

        mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        last_ts = 0.0
        for ev in self.events:
            delta = ev.timestamp - last_ts
            ticks = int(mido.second2tick(delta, ticks_per_beat, tempo))
            # copy the message and set the delta time
            msg = ev.message.copy(time=ticks)
            track.append(msg)
            last_ts = ev.timestamp

        mid.save(str(path))

