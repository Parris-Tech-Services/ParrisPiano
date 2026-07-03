from __future__ import annotations

from typing import Iterable, List, Optional, Set, Tuple

from PyQt6.QtCore import QLineF, QRectF, Qt
from PyQt6.QtGui import QColor, QBrush, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsScene, QGraphicsView, QVBoxLayout, QWidget

from .midi_intervals import extract_note_intervals
from .models import MidiEvent


def _display_pitch(midi_note: int, transpose_semitones: int) -> int:
    return max(0, min(127, midi_note + transpose_semitones))


class PianoRollView(QWidget):
    """Horizontal piano-roll: time on X, pitch on Y, with a vertical playhead."""

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
        self._playhead: Optional[QGraphicsLineItem] = None
        self._playback_sec = 0.0
        self._total_time = 0.0

        self.colors = {
            "note": QColor(125, 211, 252),
            "expected": QColor(255, 122, 92),
            "bg": QColor(255, 255, 255),
            "playhead": QColor(220, 38, 38),
        }

    def set_colors(self, theme_colors: dict) -> None:
        """Update view colors based on theme."""
        self.colors["note"] = QColor(theme_colors["accent"])
        self.colors["bg"] = QColor(theme_colors["bg"])
        self.view.setBackgroundBrush(QBrush(self.colors["bg"]))
        self.refresh_items()
        if self._playhead is not None:
            self._playhead.setPen(QPen(self.colors["playhead"], 2))

    def refresh_items(self) -> None:
        for item in self.scene.items():
            note = item.data(0)
            if note is not None:
                item.setBrush(QBrush(self.colors["note"]))

    def clear(self) -> None:
        self.scene.clear()
        self.note_items = []
        self._playhead = None

    def load_notes(
        self,
        events: Iterable[MidiEvent],
        learning_channel: int | None,
        learning_track: int | None,
        total_time: float,
        show_all: bool = False,
        learning_tracks: set[int] | None = None,
        transpose_semitones: int = 0,
    ) -> int:
        """Render note rectangles for the learning part(s). Uses same transposition as playback/tutor."""
        self.clear()
        self._total_time = total_time
        intervals, _notes_seen = extract_note_intervals(
            events, learning_channel, learning_track, show_all=show_all, learning_tracks=learning_tracks
        )

        displayed = [_display_pitch(n, transpose_semitones) for n, _s, _d in intervals]
        if displayed:
            self.min_note = min(displayed)
            self.max_note = max(displayed)
        else:
            self.min_note = 21
            self.max_note = 108

        for (note, start, dur), disp in zip(intervals, displayed, strict=True):
            self._add_note_rect(disp, start, dur)

        width = total_time * self.scale_x + 200
        height = (self.max_note - self.min_note + 1) * self.note_h
        self.scene.setSceneRect(0, 0, width, height)
        self.view.centerOn(0, height / 2)
        self._playback_sec = 0.0
        self._sync_playhead_line()
        return len(intervals)

    def _add_note_rect(self, note: int, start: float, dur: float) -> None:
        x = start * self.scale_x
        y = (self.max_note - note) * self.note_h
        rect = QRectF(x, y, max(dur * self.scale_x, 2), self.note_h - 1)
        color = self.colors["note"]
        item = self.scene.addRect(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
        item.setData(0, note)
        self.note_items.append((note, start, rect))

    def _sync_playhead_line(self) -> None:
        h = self.scene.height()
        if h <= 0:
            h = max((self.max_note - self.min_note + 1) * self.note_h, 100)
        x = self._playback_sec * self.scale_x
        if self._playhead is None:
            self._playhead = self.scene.addLine(
                QLineF(x, 0, x, h), QPen(self.colors["playhead"], 2)
            )
            self._playhead.setZValue(1000)
            self._playhead.setData(0, None)
        else:
            self._playhead.setLine(QLineF(x, 0, x, h))

    def set_playback_time(self, time_sec: float) -> None:
        """Move the vertical playhead to match playback (call from UI thread)."""
        self._playback_sec = max(0.0, time_sec)
        if self.scene.items() and self._playhead is None:
            self._sync_playhead_line()
        elif self._playhead is not None:
            h = self.scene.height()
            x = self._playback_sec * self.scale_x
            self._playhead.setLine(QLineF(x, 0, x, h))
        self.ensure_time_visible(self._playback_sec)

    def highlight_expected(self, notes: Set[int], time_sec: float) -> None:
        for item in self.scene.items():
            if item is self._playhead:
                continue
            note = item.data(0)
            if note is None:
                continue
            brush = QBrush(self.colors["note"])
            if note in notes:
                brush = QBrush(self.colors["expected"])
            item.setBrush(brush)
        self.set_playback_time(time_sec)

    def ensure_time_visible(self, time_sec: float) -> None:
        x = time_sec * self.scale_x
        view_height = self.scene.height()
        self.view.ensureVisible(x - 40, 0, 80, view_height, 20, 0)
