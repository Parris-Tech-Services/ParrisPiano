from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import mido
from loguru import logger

from .models import MidiEvent, MidiPart


def parse_midi(path: Path) -> Tuple[List[MidiPart], List[MidiEvent], float]:
    """Parse MIDI with tempo map; return parts, absolute-second events, total length seconds."""
    mid = mido.MidiFile(path)
    tempo = 500000  # default 120 bpm
    ticks_per_beat = mid.ticks_per_beat

    parts: List[MidiPart] = []
    events: List[MidiEvent] = []
    max_time_sec = 0.0

    for ti, track in enumerate(mid.tracks):
        abs_sec = 0.0
        note_count = 0
        channel_guess = None
        for msg in track:
            abs_sec += mido.tick2second(msg.time, ticks_per_beat, tempo)
            if msg.type == "set_tempo":
                tempo = msg.tempo
            if msg.type in {"note_on", "note_off"}:
                channel_guess = getattr(msg, "channel", None)
                note_count += 1
                events.append(MidiEvent(time=abs_sec, message=msg, track_index=ti, channel=channel_guess))
        parts.append(
            MidiPart(
                name=track.name if hasattr(track, "name") else f"Track {ti}",
                channel=channel_guess,
                track_index=ti,
                note_count=note_count,
            )
        )
        max_time_sec = max(max_time_sec, abs_sec)

    events.sort(key=lambda e: e.time)
    logger.info(f"Parsed MIDI: {path} tracks={len(parts)} events={len(events)} length={max_time_sec:.2f}s")
    return parts, events, max_time_sec
