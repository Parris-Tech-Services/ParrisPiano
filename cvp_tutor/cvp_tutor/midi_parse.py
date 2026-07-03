from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import mido
from loguru import logger

from .models import MidiEvent, MidiPart


GM_PROGRAMS = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
    "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavinet",
    "Celesta", "Glockenspiel", "Music Box", "Vibraphone",
    "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ",
    "Reed Organ", "Accordion", "Harmonica", "Tango Accordion",
    "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)", "Electric Guitar (jazz)", "Electric Guitar (clean)",
    "Electric Guitar (muted)", "Overdriven Guitar", "Distortion Guitar", "Guitar harmonics",
    "Acoustic Bass", "Electric Bass (finger)", "Electric Bass (pick)", "Fretless Bass",
    "Slap Bass 1", "Slap Bass 2", "Synth Bass 1", "Synth Bass 2",
    "Violin", "Viola", "Cello", "Contrabass",
    "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp", "Timpani",
    "String Ensemble 1", "String Ensemble 2", "SynthStrings 1", "SynthStrings 2",
    "Choir Aahs", "Voice Oohs", "Synth Voice", "Orchestra Hit",
    "Trumpet", "Trombone", "Tuba", "Muted Trumpet",
    "French Horn", "Brass Section", "SynthBrass 1", "SynthBrass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax",
    "Oboe", "English Horn", "Bassoon", "Clarinet",
    "Piccolo", "Flute", "Recorder", "Pan Flute",
    "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina",
    "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)", "Lead 4 (chiff)",
    "Lead 5 (charang)", "Lead 6 (voice)", "Lead 7 (fifths)", "Lead 8 (bass + lead)",
    "Pad 1 (new age)", "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)",
    "Pad 5 (bowed)", "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)",
    "FX 1 (rain)", "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)",
    "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)",
    "Sitar", "Banjo", "Shamisen", "Koto",
    "Kalimba", "Bagpipe", "Fiddle", "Shanai",
    "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock",
    "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal",
    "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet",
    "Telephone Ring", "Helicopter", "Applause", "Gunshot",
]


def _program_name(prog: int | None) -> str:
    if prog is None:
        return "Unknown"
    if 0 <= prog < len(GM_PROGRAMS):
        return GM_PROGRAMS[prog]
    return f"Program {prog}"


def parse_midi(path: Path) -> Tuple[List[MidiPart], List[MidiEvent], float]:
    """Parse MIDI with tempo map; return parts, absolute-second events, total length seconds."""
    mid = mido.MidiFile(path)
    tempo = 500000  # default 120 bpm
    ticks_per_beat = mid.ticks_per_beat
    split_by_channel = len(mid.tracks) == 1

    parts: List[MidiPart] = []
    events: List[MidiEvent] = []
    max_time_sec = 0.0
    channel_counts: dict[int, int] = {}
    channel_program: dict[int, int] = {}

    for ti, track in enumerate(mid.tracks):
        abs_sec = 0.0
        note_count = 0
        channel_guess = None
        track_program = None
        for msg in track:
            abs_sec += mido.tick2second(msg.time, ticks_per_beat, tempo)
            if msg.type == "set_tempo":
                tempo = msg.tempo
            if msg.type == "program_change":
                channel_program[getattr(msg, "channel", 0)] = msg.program
                track_program = msg.program
                if channel_guess is None:
                    channel_guess = getattr(msg, "channel", None)
            if msg.type in {"note_on", "note_off"}:
                channel_guess = getattr(msg, "channel", None)
                note_count += 1
                track_idx = channel_guess if split_by_channel and channel_guess is not None else ti
                events.append(MidiEvent(time=abs_sec, message=msg, track_index=track_idx, channel=channel_guess))
                if split_by_channel and channel_guess is not None:
                    channel_counts[channel_guess] = channel_counts.get(channel_guess, 0) + 1
        if not split_by_channel:
            prog_name = _program_name(track_program if track_program is not None else channel_program.get(channel_guess, None))
            raw_name = getattr(track, "name", "") or ""
            clean_name = raw_name.strip()
            if not clean_name or clean_name.lower() == "winjammer demo":
                base_name = prog_name
            else:
                base_name = clean_name
            parts.append(
                MidiPart(
                    name=base_name,
                    channel=channel_guess,
                    track_index=ti,
                    note_count=note_count,
                )
            )
        max_time_sec = max(max_time_sec, abs_sec)

    if split_by_channel:
        for ch, count in sorted(channel_counts.items()):
            prog_name = _program_name(channel_program.get(ch, None))
            parts.append(MidiPart(name=f"{prog_name}", channel=ch, track_index=ch, note_count=count))

    events.sort(key=lambda e: e.time)
    logger.info(f"Parsed MIDI: {path} tracks={len(parts)} events={len(events)} length={max_time_sec:.2f}s")
    return parts, events, max_time_sec
