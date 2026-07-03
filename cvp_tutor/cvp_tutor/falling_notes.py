from __future__ import annotations

from typing import Iterable, List, Optional, Set, Tuple

from PyQt6.QtCore import QLineF, QRectF, Qt
from PyQt6.QtGui import QColor, QBrush, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsScene, QGraphicsView, QVBoxLayout, QWidget

from .midi_intervals import extract_note_intervals
from .models import MidiEvent


def _display_pitch(midi_note: int, transpose_semitones: int) -> int:
    return max(0, min(127, midi_note + transpose_semitones))


class FallingNotesView(QWidget):
    """Synthesia-style lanes: notes fall toward a hit line as playback time advances."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.px_per_sec = 150.0
        self.hit_margin = 72.0
        self._intervals: List[Tuple[int, float, float]] = []
        self._min_note = 21
        self._max_note = 108
        self._playback_sec = 0.0
        self._expected: Set[int] = set()
        self._hit_line: Optional[QGraphicsLineItem] = None

        self.colors = {
            "note": QColor(125, 211, 252),
            "expected": QColor(255, 122, 92),
            "bg": QColor(255, 255, 255),
            "hit": QColor(100, 100, 100),
        }

    def set_colors(self, theme_colors: dict) -> None:
        self.colors["note"] = QColor(theme_colors["accent"])
        self.colors["bg"] = QColor(theme_colors["bg"])
        self.view.setBackgroundBrush(QBrush(self.colors["bg"]))
        self._redraw()

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
        raw_intervals, _notes_seen = extract_note_intervals(
            events, learning_channel, learning_track, show_all=show_all, learning_tracks=learning_tracks
        )
        # Store displayed MIDI (matches keyboard / tutor expectation when transposed)
        self._intervals = [
            (_display_pitch(n, transpose_semitones), t0, dur) for n, t0, dur in raw_intervals
        ]
        disps = [n for n, _t, _d in self._intervals]
        if disps:
            self._min_note = min(disps)
            self._max_note = max(disps)
        else:
            self._min_note = 21
            self._max_note = 108
        self._playback_sec = 0.0
        self._size_scene()
        self._redraw()
        return len(self._intervals)

    def _size_scene(self) -> None:
        vw = self.view.viewport().width() if self.view.viewport().width() > 0 else self.view.width()
        w = max(640, vw if vw > 0 else 800)
        # Enough vertical space for ~6 s of notes above the hit line
        h = max(380, int(self.hit_margin + 6.0 * self.px_per_sec + 48))
        self.scene.setSceneRect(0, 0, w, h)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._intervals:
            self._size_scene()
            self._redraw()

    def highlight_expected(self, notes: Set[int], time_sec: float) -> None:
        self._expected = set(notes) if notes else set()
        self.set_playback_time(time_sec)

    def set_playback_time(self, time_sec: float) -> None:
        self._playback_sec = max(0.0, time_sec)
        self._redraw()

    def _lane_rect(self, note: int, y0: float, y1: float, w: float) -> Tuple[float, float, float, float]:
        span = max(1, self._max_note - self._min_note + 1)
        pad = 8.0
        lane_w = (w - 2 * pad) / span
        x = pad + (note - self._min_note) * lane_w
        top = min(y0, y1)
        bot = max(y0, y1)
        return x, top, lane_w - 1, max(4.0, bot - top)

    def _redraw(self) -> None:
        self.scene.clear()
        self._hit_line = None

        rect = self.scene.sceneRect()
        w = rect.width()
        h = rect.height()
        hit_y = h - self.hit_margin

        pen = QPen(self.colors["hit"], 2)
        self._hit_line = self.scene.addLine(QLineF(0, hit_y, w, hit_y), pen)
        self._hit_line.setZValue(500)

        t_now = self._playback_sec
        # Visible window: a few seconds ahead / behind
        for note, t0, dur in self._intervals:
            t1 = t0 + dur
            if t1 < t_now - 0.15:
                continue
            if t0 > t_now + 8.0:
                continue
            dt0 = t0 - t_now
            dt1 = t1 - t_now
            y0 = hit_y - dt0 * self.px_per_sec
            y1 = hit_y - dt1 * self.px_per_sec
            x, top, lw, lh = self._lane_rect(note, y0, y1, w)
            r = QRectF(x, top, lw, lh)
            col = self.colors["expected"] if note in self._expected else self.colors["note"]
            item = self.scene.addRect(r, QPen(Qt.PenStyle.NoPen), QBrush(col))
            item.setData(0, note)
            item.setZValue(100)
