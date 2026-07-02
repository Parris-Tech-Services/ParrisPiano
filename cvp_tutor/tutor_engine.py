from __future__ import annotations

from typing import Iterable, List

from loguru import logger

from .models import ExpectedChord, MidiEvent


class TutorEngine:
    """Groups learning-part notes into chords and waits for user to match them."""

    def __init__(self, chord_window_ms: int = 40, strict: bool = False) -> None:
        self.chord_window = chord_window_ms / 1000.0
        self.strict = strict
        self.chords: List[ExpectedChord] = []

    def build_expected(self, events: Iterable[MidiEvent], learning_channel: int | None, learning_track: int | None) -> List[ExpectedChord]:
        filtered = [
            ev for ev in events
            if ev.message.type == "note_on" and ev.message.velocity > 0
            and ((learning_channel is None) or (ev.channel == learning_channel))
            and ((learning_track is None) or (ev.track_index == learning_track))
        ]
        filtered.sort(key=lambda e: e.time)

        chords: List[ExpectedChord] = []
        for ev in filtered:
            if not chords or (ev.time - chords[-1].time) > self.chord_window:
                chords.append(ExpectedChord(time=ev.time, notes={ev.message.note}, track_index=ev.track_index, channel=ev.channel))
            else:
                chords[-1].notes.add(ev.message.note)

        self.chords = chords
        logger.info(f"Built {len(chords)} expected chords for tutor mode")
        return chords

