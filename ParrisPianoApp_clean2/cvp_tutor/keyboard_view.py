from __future__ import annotations

from typing import Set

from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF


class KeyboardView(QWidget):
    """Minimal 88-key view highlighting expected and pressed notes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.held_notes: Set[int] = set()
        self.expected_notes: Set[int] = set()
        self.setAutoFillBackground(False)

    def set_held(self, notes: Set[int]) -> None:
        self.held_notes = set(notes)
        self.update()

    def set_expected(self, notes: Set[int]) -> None:
        self.expected_notes = set(notes)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        width = self.width()
        height = self.height()
        key_count = 88
        white_keys = []
        black_keys = []
        key_width = width / 52  # 52 white keys
        # MIDI note 21 (A0) to 108 (C8)
        note = 21
        x_white = 0.0
        for _ in range(key_count):
            pc = note % 12
            is_black = pc in {1, 3, 6, 8, 10}
            if is_black:
                black_keys.append((note, x_white - key_width * 0.35, key_width * 0.7))
            else:
                white_keys.append((note, x_white, key_width))
                x_white += key_width
            note += 1

        # Draw white keys
        for note, x, w in white_keys:
            rect = QRectF(x, 0, w, height)
            color = QColor(245, 246, 248)
            if note in self.expected_notes:
                color = QColor(125, 211, 252)
            if note in self.held_notes:
                color = QColor(255, 122, 92)
            painter.setPen(QPen(QColor(30, 30, 30)))
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)

        # Draw black keys
        for note, x, w in black_keys:
            rect = QRectF(x, 0, w, height * 0.6)
            color = QColor(30, 30, 35)
            if note in self.expected_notes:
                color = QColor(80, 150, 220)
            if note in self.held_notes:
                color = QColor(255, 122, 92)
            painter.setPen(QPen(Qt.GlobalColor.black))
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)

