from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import mido
from loguru import logger

from .models import MidiEvent, MidiPart


def _build_tempo_points(mid: mido.MidiFile) -> List[tuple[int, int]]:
    points: dict[int, int] = {0: 500000}
    for track in mid.tracks:
        absolute_ticks = 0
        for msg in track:
            absolute_ticks += msg.time
            if msg.type == "set_tempo":
                points[absolute_ticks] = msg.tempo
    return sorted(points.items(), key=lambda item: item[0])


def _ticks_to_seconds(target_tick: int, tempo_points: List[tuple[int, int]], ticks_per_beat: int) -> float:
    total_seconds = 0.0
    current_tick = 0
    current_tempo = tempo_points[0][1]

    for tick, tempo in tempo_points[1:]:
        if target_tick <= tick:
            break
        total_seconds += mido.tick2second(tick - current_tick, ticks_per_beat, current_tempo)
        current_tick = tick
        current_tempo = tempo

    total_seconds += mido.tick2second(target_tick - current_tick, ticks_per_beat, current_tempo)
    return total_seconds


def _build_time_signature_points(mid: mido.MidiFile) -> List[tuple[int, int, int]]:
    points: dict[int, tuple[int, int]] = {0: (4, 4)}
    for track in mid.tracks:
        absolute_ticks = 0
        for msg in track:
            absolute_ticks += msg.time
            if msg.type == "time_signature":
                points[absolute_ticks] = (msg.numerator, msg.denominator)
    return [(tick, numer, denom) for tick, (numer, denom) in sorted(points.items(), key=lambda item: item[0])]


def build_time_signatures(path: Path) -> List[tuple[float, int, int]]:
    mid = mido.MidiFile(path)
    tempo_points = _build_tempo_points(mid)
    ticks_per_beat = mid.ticks_per_beat
    return [
        (_ticks_to_seconds(tick, tempo_points, ticks_per_beat), numer, denom)
        for tick, numer, denom in _build_time_signature_points(mid)
    ]


def build_barlines(path: Path) -> List[float]:
    """Return measure start times in seconds using tempo and time-signature changes."""
    mid = mido.MidiFile(path)
    tempo_points = _build_tempo_points(mid)
    time_sig_points = _build_time_signature_points(mid)
    ticks_per_beat = mid.ticks_per_beat

    max_tick = 0
    for track in mid.tracks:
        absolute_ticks = 0
        for msg in track:
            absolute_ticks += msg.time
        max_tick = max(max_tick, absolute_ticks)

    barlines: List[float] = [0.0]
    ts_index = 0
    current_tick = 0
    while current_tick <= max_tick:
        while ts_index + 1 < len(time_sig_points) and time_sig_points[ts_index + 1][0] <= current_tick:
            ts_index += 1
        _, numerator, denominator = time_sig_points[ts_index]
        beats_per_bar = numerator * (4 / denominator)
        ticks_per_bar = int(beats_per_bar * ticks_per_beat)
        if ticks_per_bar <= 0:
            break
        current_tick += ticks_per_bar
        if current_tick <= max_tick:
            barlines.append(_ticks_to_seconds(current_tick, tempo_points, ticks_per_beat))
    return barlines


def parse_midi(path: Path) -> Tuple[List[MidiPart], List[MidiEvent], float]:
    """Parse MIDI with a global tempo map and return part metadata plus absolute-second events."""
    mid = mido.MidiFile(path)
    tempo_points = _build_tempo_points(mid)
    ticks_per_beat = mid.ticks_per_beat

    parts: List[MidiPart] = []
    events: List[MidiEvent] = []
    max_time_sec = 0.0

    for track_index, track in enumerate(mid.tracks):
        absolute_ticks = 0
        note_count = 0
        channel_guess = None

        for msg in track:
            absolute_ticks += msg.time
            absolute_seconds = _ticks_to_seconds(absolute_ticks, tempo_points, ticks_per_beat)

            if msg.type in {"note_on", "note_off"}:
                channel_guess = getattr(msg, "channel", channel_guess)
                note_count += 1
                events.append(
                    MidiEvent(
                      time=absolute_seconds,
                      message=msg,
                      track_index=track_index,
                      channel=channel_guess,
                    )
                )

            max_time_sec = max(max_time_sec, absolute_seconds)

        parts.append(
            MidiPart(
                name=track.name if hasattr(track, "name") else f"Track {track_index}",
                channel=channel_guess,
                track_index=track_index,
                note_count=note_count,
            )
        )

    events.sort(key=lambda event: event.time)
    logger.info(f"Parsed MIDI: {path} tracks={len(parts)} events={len(events)} length={max_time_sec:.2f}s")
    return parts, events, max_time_sec
