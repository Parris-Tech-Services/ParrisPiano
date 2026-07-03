from __future__ import annotations

import queue
import threading
import time
from typing import Callable, List, Optional

import mido
from loguru import logger


def _set_backend():
    try:
        mido.set_backend("mido.backends.rtmidi")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to set rtmidi backend: {exc}")


class MidiEngine:
    """Handles MIDI device discovery, input callbacks, and outbound sends."""

    def __init__(self) -> None:
        _set_backend()
        self.input_port: Optional[mido.ports.BaseInput] = None
        self.output_port: Optional[mido.ports.BaseOutput] = None
        self._listeners: List[Callable[[mido.Message], None]] = []
        self._in_queue: "queue.Queue[mido.Message]" = queue.Queue()
        self._lock = threading.Lock()

    def list_inputs(self) -> List[str]:
        return mido.get_input_names()

    def list_outputs(self) -> List[str]:
        return mido.get_output_names()

    def open_ports(self, input_name: Optional[str], output_name: Optional[str]) -> None:
        self.close_ports()
        if input_name:
            logger.info(f"Opening MIDI IN: {input_name}")
            self.input_port = mido.open_input(input_name, callback=self._handle_input)
        if output_name:
            logger.info(f"Opening MIDI OUT: {output_name}")
            self.output_port = mido.open_output(output_name)

    def close_ports(self) -> None:
        if self.input_port:
            logger.debug("Closing MIDI IN")
            self.input_port.close()
        if self.output_port:
            logger.debug("Closing MIDI OUT")
            self.output_port.close()
        self.input_port = None
        self.output_port = None

    def register_listener(self, fn: Callable[[mido.Message], None]) -> None:
        self._listeners.append(fn)

    def _handle_input(self, msg: mido.Message) -> None:
        logger.debug(f"MIDI IN: {msg}")
        self._in_queue.put(msg)
        for fn in self._listeners:
            try:
                fn(msg)
            except Exception as exc:  # pragma: no cover - best effort
                logger.error(f"Listener error: {exc}")

    def send(self, msg: mido.Message) -> None:
        if self.output_port:
            logger.debug(f"MIDI OUT: {msg}")
            self.output_port.send(msg)

    def send_test_tone(self, channel: int = 0, duration_ms: int = 400, velocity: int = 96) -> None:
        if not self.output_port:
            logger.warning("No MIDI OUT selected for test tone")
            return
        note = 60
        on = mido.Message("note_on", note=note, velocity=velocity, channel=channel)
        off = mido.Message("note_off", note=note, velocity=0, channel=channel)
        self.send(on)
        threading.Timer(duration_ms / 1000.0, lambda: self.send(off)).start()

    def wait_for_notes(
        self,
        expected_notes: set[int],
        timeout: float,
        strict: bool,
    ) -> bool:
        """Blocks until expected notes are played (NoteOn)."""
        deadline = time.time() + timeout
        seen: set[int] = set()
        while time.time() < deadline:
            try:
                msg = self._in_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            if msg.type == "note_on" and msg.velocity > 0:
                seen.add(msg.note)
                if (strict and seen == expected_notes) or (not strict and expected_notes.issubset(seen)):
                    return True
        return False

