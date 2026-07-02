from __future__ import annotations

import queue
import time
import threading
from typing import Callable, List, Optional

import mido
from loguru import logger


class MidiIO:
    """Enumerate/open MIDI ports and fan out input events."""

    def __init__(self) -> None:
        self._set_backend()
        self.input_port: Optional[mido.ports.BaseInput] = None
        self.output_port: Optional[mido.ports.BaseOutput] = None
        self._listeners: List[Callable[[mido.Message], None]] = []
        self._queue: "queue.Queue[mido.Message]" = queue.Queue()
        self._lock = threading.Lock()

    def _set_backend(self) -> None:
        try:
            mido.set_backend("mido.backends.rtmidi")
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Could not set rtmidi backend: {exc}")

    def list_inputs(self) -> List[str]:
        return mido.get_input_names()

    def list_outputs(self) -> List[str]:
        return mido.get_output_names()

    def open(self, input_name: Optional[str], output_name: Optional[str]) -> None:
        self.close()
        if input_name:
            logger.info(f"Opening MIDI IN: {input_name}")
            self.input_port = mido.open_input(input_name, callback=self._handle_in)
        if output_name:
            logger.info(f"Opening MIDI OUT: {output_name}")
            self.output_port = mido.open_output(output_name)

    def close(self) -> None:
        if self.input_port:
            self.input_port.close()
        if self.output_port:
            self.output_port.close()
        self.input_port = None
        self.output_port = None

    def send(self, msg: mido.Message) -> None:
        if self.output_port:
            logger.debug(f"MIDI OUT: {msg}")
            self.output_port.send(msg)

    def register_listener(self, fn: Callable[[mido.Message], None]) -> None:
        self._listeners.append(fn)

    def _handle_in(self, msg: mido.Message) -> None:
        logger.debug(f"MIDI IN: {msg}")
        self._queue.put(msg)
        for fn in self._listeners:
            try:
                fn(msg)
            except Exception as exc:  # pragma: no cover
                logger.error(f"MIDI listener error: {exc}")

    def poll(self, timeout: float = 0.05) -> Optional[mido.Message]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def wait_for_notes(self, expected_notes: set[int], timeout: float, strict: bool) -> bool:
        """Blocks until expected notes are played (NoteOn)."""
        deadline = time.time() + timeout
        seen: set[int] = set()
        while time.time() < deadline:
            msg = self.poll(timeout=0.05)
            if not msg:
                continue
            if msg.type == "note_on" and msg.velocity > 0:
                seen.add(msg.note)
                if (strict and seen == expected_notes) or (not strict and expected_notes.issubset(seen)):
                    return True
        return False

    def send_test_tone(self, channel: int = 0, duration_ms: int = 400, velocity: int = 96) -> None:
        if not self.output_port:
            logger.warning("No MIDI OUT selected for test tone")
            return
        note = 60
        on = mido.Message("note_on", note=note, velocity=velocity, channel=channel)
        off = mido.Message("note_off", note=note, velocity=0, channel=channel)
        self.send(on)
        threading.Timer(duration_ms / 1000.0, lambda: self.send(off)).start()
