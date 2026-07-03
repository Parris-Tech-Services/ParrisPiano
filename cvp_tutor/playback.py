from __future__ import annotations

import threading
import time
from typing import Callable, Iterable, List, Optional, Set

import mido
from loguru import logger

from .midi_io import MidiIO
from .models import MidiEvent


class PlaybackEngine:
    """Simple scheduler for MIDI events with tempo, transpose, loop, mute/solo."""

    def __init__(self, midi: MidiIO) -> None:
        self.midi = midi
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self.on_status: Optional[Callable[[str], None]] = None
        self.muted_tracks: Set[int] = set()
        self.solo_tracks: Set[int] = set()

    def set_status_callback(self, fn: Callable[[str], None]) -> None:
        self.on_status = fn

    def play(
        self,
        events: List[MidiEvent],
        tempo_mult: float = 1.0,
        transpose: int = 0,
        loop_start: float = 0.0,
        loop_end: Optional[float] = None,
    ) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_flag.clear()
        self.thread = threading.Thread(
            target=self._run,
            args=(events, tempo_mult, transpose, loop_start, loop_end),
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_flag.set()

    def _run(
        self,
        events: Iterable[MidiEvent],
        tempo_mult: float,
        transpose: int,
        loop_start: float,
        loop_end: Optional[float],
    ) -> None:
        def status(msg: str) -> None:
            if self.on_status:
                self.on_status(msg)

        start = time.perf_counter()
        for ev in events:
            if self.stop_flag.is_set():
                status("Stopped.")
                return
            if ev.time < loop_start:
                continue
            if loop_end and ev.time > loop_end:
                break
            if self.solo_tracks and ev.track_index not in self.solo_tracks:
                continue
            if ev.track_index in self.muted_tracks:
                continue

            target = start + (ev.time - loop_start) / max(tempo_mult, 0.01)
            while not self.stop_flag.is_set() and time.perf_counter() < target:
                time.sleep(0.001)

            msg = ev.message.copy()
            if msg.type in {"note_on", "note_off"} and transpose:
                msg.note = max(0, min(127, msg.note + transpose))
            if msg.type.startswith("note") or msg.type.startswith("control"):
                self.midi.send(msg)
        status("Playback finished.")
