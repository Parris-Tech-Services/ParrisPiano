from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QVBoxLayout, QWidget

from .models import MidiEvent


NATURAL_STEPS = {
    0: (0, ""),
    1: (0, "#"),
    2: (1, ""),
    3: (1, "#"),
    4: (2, ""),
    5: (3, ""),
    6: (3, "#"),
    7: (4, ""),
    8: (4, "#"),
    9: (5, ""),
    10: (5, "#"),
    11: (6, ""),
}


def note_staff_position(note: int) -> tuple[int, str]:
    octave = (note // 12) - 1
    pitch_class = note % 12
    diatonic_offset, accidental = NATURAL_STEPS[pitch_class]
    diatonic_index = (octave - 4) * 7 + diatonic_offset
    return diatonic_index, accidental


def note_y(note: int, middle_c_y: float, diatonic_step_px: float) -> float:
    diatonic_index, _ = note_staff_position(note)
    return middle_c_y - diatonic_index * (diatonic_step_px / 2.0)


def pitch_uses_treble_staff(note: int) -> bool:
    return note >= 60


@dataclass(frozen=True)
class RenderedNote:
    note: int
    start: float
    duration: float


@dataclass(frozen=True)
class RenderedRest:
    start: float
    duration: float
    treble: bool


def build_rendered_notes(
    events: Sequence[MidiEvent],
    learning_channel: int | None,
    learning_track: int | None,
) -> List[RenderedNote]:
    active: dict[tuple[int, int | None], list[float]] = {}
    rendered: List[RenderedNote] = []
    filtered = [
        ev for ev in events
        if (learning_channel is None or ev.channel == learning_channel)
        and (learning_track is None or ev.track_index == learning_track)
        and ev.message.type in {"note_on", "note_off"}
    ]
    filtered.sort(key=lambda ev: ev.time)

    for ev in filtered:
        msg = ev.message
        key = (msg.note, ev.channel)
        is_note_on = msg.type == "note_on" and msg.velocity > 0
        if is_note_on:
            active.setdefault(key, []).append(ev.time)
            continue
        starts = active.get(key)
        if not starts:
            continue
        start = starts.pop(0)
        duration = max(0.08, ev.time - start)
        rendered.append(RenderedNote(note=msg.note, start=start, duration=duration))
        if not starts:
            active.pop(key, None)

    for (note, _channel), starts in active.items():
        for start in starts:
            rendered.append(RenderedNote(note=note, start=start, duration=0.3))

    rendered.sort(key=lambda item: (item.start, item.note))
    return rendered


def build_rests(notes: Sequence[RenderedNote], total_time: float, treble: bool, gap_threshold: float = 0.65) -> List[RenderedRest]:
    relevant = [note for note in notes if pitch_uses_treble_staff(note.note) == treble]
    if not relevant:
        return []

    rests: List[RenderedRest] = []
    cursor = relevant[0].start
    for note in relevant:
        gap = note.start - cursor
        if gap >= gap_threshold:
            rests.append(RenderedRest(start=cursor, duration=gap, treble=treble))
        cursor = max(cursor, note.start + note.duration)

    tail_gap = total_time - cursor
    if tail_gap >= gap_threshold:
        rests.append(RenderedRest(start=cursor, duration=tail_gap, treble=treble))
    return rests


class NotationRollView(QWidget):
    """Scrolling notation lane with simplified score cues driven by MIDI timing."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: #f8fafc; border: 1px solid #d7dde8; border-radius: 6px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.scale_x = 140.0
        self.staff_gap = 11.0
        self.middle_c_y = 92.0
        self.note_head_w = 12.0
        self.note_head_h = 8.0
        self.left_margin = 84.0
        self.playhead = None
        self.note_items: List[tuple[object, Set[int], float]] = []
        self.rendered_notes: List[RenderedNote] = []
        self.rendered_rests: List[RenderedRest] = []

    def clear(self) -> None:
        self.scene.clear()
        self.note_items = []
        self.rendered_notes = []
        self.rendered_rests = []
        self.playhead = None

    def load_score(
        self,
        notes: Sequence[RenderedNote],
        total_time: float,
        barlines: List[float] | None = None,
        time_signatures: List[tuple[float, int, int]] | None = None,
    ) -> None:
        self.clear()
        self.rendered_notes = list(notes)
        self.rendered_rests = build_rests(self.rendered_notes, total_time, treble=True) + build_rests(
            self.rendered_notes, total_time, treble=False
        )
        self._draw_staff(barlines or [], time_signatures or [])
        self._draw_rests()
        self._draw_notes()

        width = max(total_time * self.scale_x + self.left_margin + 220, 800)
        height = 196
        self.scene.setSceneRect(0, 0, width, height)
        self.playhead = self.scene.addLine(0, 0, 0, height, QPen(QColor(37, 99, 235), 2))
        self.view.centerOn(0, height / 2)

    def _draw_staff(self, barlines: List[float], time_signatures: List[tuple[float, int, int]]) -> None:
        line_pen = QPen(QColor(71, 85, 105), 1.2)
        accent_pen = QPen(QColor(100, 116, 139), 1, Qt.PenStyle.DashLine)
        barline_pen = QPen(QColor(51, 65, 85), 1.3)
        left = self.left_margin
        right = 5000
        treble_top = 26
        bass_top = 112

        for i in range(5):
            y = treble_top + i * self.staff_gap
            self.scene.addLine(left, y, right, y, line_pen)
        for i in range(5):
            y = bass_top + i * self.staff_gap
            self.scene.addLine(left, y, right, y, line_pen)
        self.scene.addLine(left, self.middle_c_y, right, self.middle_c_y, accent_pen)

        brace_pen = QPen(QColor(30, 41, 59), 2.2)
        self.scene.addLine(left - 12, treble_top, left - 12, bass_top + 4 * self.staff_gap, brace_pen)

        clef_font = QFont("Segoe UI Symbol", 28)
        treble = self.scene.addText("\U0001D11E", clef_font)
        treble.setDefaultTextColor(QColor(15, 23, 42))
        treble.setPos(18, 18)
        bass = self.scene.addText("\U0001D122", clef_font)
        bass.setDefaultTextColor(QColor(15, 23, 42))
        bass.setPos(22, 104)

        time_sig_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        for time_sec, numerator, denominator in time_signatures:
            x = self.left_margin + time_sec * self.scale_x + 8
            numer = self.scene.addText(str(numerator), time_sig_font)
            numer.setDefaultTextColor(QColor(15, 23, 42))
            numer.setPos(x, treble_top + self.staff_gap * 0.35)
            denom = self.scene.addText(str(denominator), time_sig_font)
            denom.setDefaultTextColor(QColor(15, 23, 42))
            denom.setPos(x, treble_top + self.staff_gap * 2.0)

        for bar_time in barlines:
            x = self.left_margin + bar_time * self.scale_x
            self.scene.addLine(x, treble_top, x, treble_top + 4 * self.staff_gap, barline_pen)
            self.scene.addLine(x, bass_top, x, bass_top + 4 * self.staff_gap, barline_pen)

    def _draw_rests(self) -> None:
        pen = QPen(QColor(30, 41, 59), 1.5)
        brush = QBrush(QColor(30, 41, 59))
        for rest in self.rendered_rests:
            x = self.left_margin + rest.start * self.scale_x
            width = min(18.0, max(10.0, rest.duration * self.scale_x * 0.28))
            y = 54 if rest.treble else 140
            self.scene.addRect(QRectF(x, y, width, 4), pen, brush)
            self.scene.addLine(x + width * 0.5, y + 4, x + width * 0.5, y + 12, pen)

    def _draw_notes(self) -> None:
        grouped: dict[float, List[RenderedNote]] = {}
        for note in self.rendered_notes:
            bucket = round(note.start / 0.001) * 0.001
            grouped.setdefault(bucket, []).append(note)

        sorted_groups = sorted(grouped.items(), key=lambda item: item[0])
        for idx, (group_time, notes) in enumerate(sorted_groups):
            chord_notes = {note.note for note in notes}
            positions: list[tuple[RenderedNote, QRectF, bool]] = []
            for rendered in sorted(notes, key=lambda item: item.note):
                x = self.left_margin + rendered.start * self.scale_x
                width = max(self.note_head_w, min(34.0, rendered.duration * self.scale_x))
                y = note_y(rendered.note, self.middle_c_y, self.staff_gap)
                rect = QRectF(x, y, width, self.note_head_h)
                accidental = note_staff_position(rendered.note)[1]
                if accidental:
                    accidental_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
                    accidental_item = self.scene.addText(accidental, accidental_font)
                    accidental_item.setDefaultTextColor(QColor(15, 23, 42))
                    accidental_item.setPos(x - 12, y - 10)
                item = self.scene.addEllipse(rect, QPen(QColor(15, 23, 42), 1), QBrush(QColor(15, 23, 42)))
                stem_up = rendered.note < 71
                stem_x = rect.right() - 1 if stem_up else rect.left() + 1
                stem_end_y = rect.center().y() - 28 if stem_up else rect.center().y() + 28
                self.scene.addLine(stem_x, rect.center().y(), stem_x, stem_end_y, QPen(QColor(15, 23, 42), 1.3))
                self._draw_ledger_lines(x, rendered.note, width)
                positions.append((rendered, rect, stem_up))
                self.note_items.append((item, chord_notes, group_time))

            next_group = sorted_groups[idx + 1][1] if idx + 1 < len(sorted_groups) else []
            self._draw_beams(notes, positions, next_group)

    def _draw_beams(
        self,
        notes: Sequence[RenderedNote],
        positions: Sequence[tuple[RenderedNote, QRectF, bool]],
        next_group: Sequence[RenderedNote],
    ) -> None:
        if not notes or not next_group:
            return
        if len(notes) != 1 or len(next_group) != 1:
            return
        left_note = notes[0]
        right_note = next_group[0]
        if left_note.duration > 0.55 or right_note.duration > 0.55:
            return
        if pitch_uses_treble_staff(left_note.note) != pitch_uses_treble_staff(right_note.note):
            return

        left_rect = positions[0][1]
        stem_up = positions[0][2]
        right_x = self.left_margin + right_note.start * self.scale_x
        right_y = note_y(right_note.note, self.middle_c_y, self.staff_gap)
        right_rect = QRectF(right_x, right_y, max(self.note_head_w, min(34.0, right_note.duration * self.scale_x)), self.note_head_h)
        pen = QPen(QColor(15, 23, 42), 5)
        if stem_up:
            self.scene.addLine(left_rect.right() - 1, left_rect.center().y() - 28, right_rect.right() - 1, right_rect.center().y() - 28, pen)
        else:
            self.scene.addLine(left_rect.left() + 1, left_rect.center().y() + 28, right_rect.left() + 1, right_rect.center().y() + 28, pen)

    def _draw_ledger_lines(self, x: float, note: int, width: float) -> None:
        pen = QPen(QColor(71, 85, 105), 1)
        center_y = note_y(note, self.middle_c_y, self.staff_gap) + self.note_head_h / 2
        treble_top = 26
        treble_bottom = treble_top + 4 * self.staff_gap
        bass_top = 112
        bass_bottom = bass_top + 4 * self.staff_gap
        if center_y < treble_top or center_y > bass_bottom:
            reference = treble_top if center_y < treble_top else bass_bottom
            direction = -self.staff_gap if center_y < treble_top else self.staff_gap
            y = reference
            while (direction < 0 and y >= center_y) or (direction > 0 and y <= center_y):
                self.scene.addLine(x - 2, y, x + width + 2, y, pen)
                y += direction
        elif treble_bottom < center_y < bass_top:
            self.scene.addLine(x - 2, self.middle_c_y, x + width + 2, self.middle_c_y, pen)

    def set_playhead(self, time_sec: float) -> None:
        if self.playhead is None:
            return
        x = max(0.0, time_sec * self.scale_x + self.left_margin)
        self.playhead.setLine(x, 0, x, self.scene.height())
        self.view.ensureVisible(x - 180, 0, 360, self.scene.height(), 120, 0)

    def highlight_expected(self, notes: Set[int]) -> None:
        for item, chord_notes, _ in self.note_items:
            if chord_notes == notes and notes:
                item.setBrush(QBrush(QColor(59, 130, 246)))
                item.setPen(QPen(QColor(29, 78, 216), 1.2))
            else:
                item.setBrush(QBrush(QColor(15, 23, 42)))
                item.setPen(QPen(QColor(15, 23, 42), 1))
