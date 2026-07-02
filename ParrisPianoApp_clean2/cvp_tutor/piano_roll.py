from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QVBoxLayout, QWidget

from .models import MidiEvent


class PianoRollView(QWidget):
    """Simple piano-roll style viewer for the learning part."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.scale_x = 120.0  # pixels per second
        self.note_h = 8.0
        self.min_note = 21
        self.max_note = 108
        self.note_items: List[Tuple[int, float, QRectF]] = []

    def clear(self) -> None:
        self.scene.clear()
        self.note_items = []

    def load_notes(self, events: Iterable[MidiEvent], learning_channel: int | None, learning_track: int | None, total_time: float, show_all: bool = False) -> int:
        """Render note rectangles for the learning part (or all parts if show_all). Returns note count."""
        self.clear()
        note_starts: Dict[Tuple[int, int | None], float] = {}
        notes_seen: List[int] = []
        intervals: List[Tuple[int, float, float]] = []
        for ev in events:
            msg = ev.message
            if msg.type == "note_on" and msg.velocity > 0:
                if not show_all:
                    if (learning_channel is not None and msg.channel != learning_channel) or (
                        learning_track is not None and ev.track_index != learning_track
                    ):
                        continue
                note_starts[(msg.note, ev.track_index)] = ev.time
                notes_seen.append(msg.note)
            elif msg.type in {"note_off", "note_on"}:
                key = (getattr(msg, "note", -1), ev.track_index)
                if key in note_starts:
                    start = note_starts.pop(key)
                    end = ev.time
                    intervals.append((key[0], start, max(end - start, 0.05)))

        # Any lingering note_on without note_off: draw small blips
        for (note, _), start in note_starts.items():
            intervals.append((note, start, 0.1))

        if notes_seen:
            self.min_note = min(notes_seen)
            self.max_note = max(notes_seen)
        else:
            self.min_note = 21
            self.max_note = 108

        for note, start, dur in intervals:
            self._add_note_rect(note, start, dur)

        # Scene bounds
        width = total_time * self.scale_x + 200
        height = (self.max_note - self.min_note + 1) * self.note_h
        self.scene.setSceneRect(0, 0, width, height)
        self.view.centerOn(0, height / 2)
        return len(intervals)

    def _add_note_rect(self, note: int, start: float, dur: float) -> None:
        x = start * self.scale_x
        y = (self.max_note - note) * self.note_h
        rect = QRectF(x, y, max(dur * self.scale_x, 2), self.note_h - 1)
        color = QColor(125, 211, 252)
        item = self.scene.addRect(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
        item.setData(0, note)
        self.note_items.append((note, start, rect))

    def highlight_expected(self, notes: Set[int], time_sec: float) -> None:
        for item in self.scene.items():
            note = item.data(0)
            if note is None:
                continue
            brush = QBrush(QColor(125, 211, 252))
            if note in notes:
                brush = QBrush(QColor(255, 122, 92))
            item.setBrush(brush)
        self.ensure_time_visible(time_sec)

    def ensure_time_visible(self, time_sec: float) -> None:
        x = time_sec * self.scale_x
        view_height = self.scene.height()
        self.view.ensureVisible(x - 40, 0, 80, view_height, 20, 0)
