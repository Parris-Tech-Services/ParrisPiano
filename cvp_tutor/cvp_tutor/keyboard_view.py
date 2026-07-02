from __future__ import annotations

from typing import Set

from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QPainterPath, QFont
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF


class KeyboardView(QWidget):
    """Minimal 88-key view highlighting expected and pressed notes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.held_notes: Set[int] = set()
        self.expected_notes: Set[int] = set()
        self.upcoming_notes: Set[int] = set()
        self.upcoming_strength = 0.0
        self.visible_min_note = 21
        self.visible_max_note = 108
        self.setAutoFillBackground(False)

    def set_held(self, notes: Set[int]) -> None:
        self.held_notes = set(notes)
        self.update()

    def set_expected(self, notes: Set[int]) -> None:
        self.expected_notes = set(notes)
        self.update()

    def set_upcoming(self, notes: Set[int], strength: float = 1.0) -> None:
        self.upcoming_notes = set(notes)
        self.upcoming_strength = max(0.0, min(1.0, strength))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = self.width()
        height = self.height()
        painter.fillRect(self.rect(), QColor(243, 246, 252))
        white_keys = []
        black_keys = []
        visible_notes = list(range(self.visible_min_note, self.visible_max_note + 1))
        white_count = sum(1 for note in visible_notes if note % 12 not in {1, 3, 6, 8, 10})
        key_width = width / max(white_count, 1)
        # Keep the keyboard visually shorter and more realistic even when the tab is tall.
        body_height = min(height - 24, max(88.0, key_width * 6.2))
        note = self.visible_min_note
        x_white = 0.0
        while note <= self.visible_max_note:
            pc = note % 12
            is_black = pc in {1, 3, 6, 8, 10}
            if is_black:
                black_keys.append((note, x_white - key_width * 0.35, key_width * 0.7))
            else:
                white_keys.append((note, x_white, key_width))
                x_white += key_width
            note += 1

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 18)))
        painter.drawRoundedRect(QRectF(2, 8, width - 4, body_height + 8), 8, 8)

        for note, x, w in white_keys:
            rect = QRectF(x, 0, w, body_height)
            color = QColor(248, 250, 252)
            if note in self.expected_notes:
                color = QColor(125, 211, 252)
            if note in self.held_notes:
                color = QColor(255, 122, 92)
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            if note in self.expected_notes or note in self.held_notes:
                gradient.setColorAt(0.0, color.lighter(110))
                gradient.setColorAt(1.0, color.darker(110))
            else:
                gradient.setColorAt(0.0, QColor(255, 255, 255))
                gradient.setColorAt(0.85, QColor(237, 241, 246))
                gradient.setColorAt(1.0, QColor(221, 227, 235))
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 2, 2)
            painter.setPen(QPen(QColor(71, 85, 105), 1))
            painter.setBrush(QBrush(gradient))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
            painter.drawLine(QPointF(rect.left() + 2, rect.top() + 3), QPointF(rect.right() - 2, rect.top() + 3))
            if note in self.upcoming_notes and note not in self.expected_notes:
                alpha = int(70 + 150 * self.upcoming_strength)
                marker = QRectF(x + w * 0.18, body_height + 6, w * 0.64, 8)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(96, 165, 250, alpha)))
                painter.drawRoundedRect(marker, 3, 3)
            if note == 60:
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)
                painter.setPen(QPen(QColor(71, 85, 105)))
                painter.drawText(QRectF(x, body_height + 12, w, 12), Qt.AlignmentFlag.AlignCenter, "C4")

        for note, x, w in black_keys:
            rect = QRectF(x, 0, w, body_height * 0.62)
            color = QColor(30, 30, 35)
            if note in self.expected_notes:
                color = QColor(80, 150, 220)
            if note in self.held_notes:
                color = QColor(255, 122, 92)
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            if note in self.expected_notes or note in self.held_notes:
                gradient.setColorAt(0.0, color.lighter(110))
                gradient.setColorAt(1.0, color.darker(120))
            else:
                gradient.setColorAt(0.0, QColor(55, 65, 81))
                gradient.setColorAt(0.2, QColor(31, 41, 55))
                gradient.setColorAt(1.0, QColor(15, 23, 42))
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 2, 2)
            painter.setPen(QPen(QColor(15, 23, 42), 1))
            painter.setBrush(QBrush(gradient))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
            painter.drawLine(QPointF(rect.left() + 2, rect.top() + 2), QPointF(rect.right() - 2, rect.top() + 2))
            if note in self.upcoming_notes and note not in self.expected_notes:
                alpha = int(70 + 150 * self.upcoming_strength)
                marker = QRectF(x + w * 0.1, body_height + 6, w * 0.8, 7)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(96, 165, 250, alpha)))
                painter.drawRoundedRect(marker, 3, 3)

