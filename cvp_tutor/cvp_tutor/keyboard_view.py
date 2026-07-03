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
        # Default colors (Classic)
        self.colors = {
            "white_key": QColor(245, 246, 248),
            "black_key": QColor(30, 30, 35),
            "expected": QColor(125, 211, 252),
            "held": QColor(255, 122, 92),
            "outline": QColor(30, 30, 30),
        }

    def set_colors(self, theme_colors: dict) -> None:
        """Update view colors based on theme."""
        # We derive key colors from the theme palette
        accent = QColor(theme_colors["accent"])
        fg = QColor(theme_colors["fg"])
        
        self.colors["expected"] = accent
        self.colors["outline"] = fg
        
        # Adjust key colors based on brightness to handle dark modes
        bg = QColor(theme_colors["bg"])
        if bg.lightness() < 128:
            # Dark theme
            self.colors["white_key"] = QColor(60, 60, 60)
            self.colors["black_key"] = QColor(20, 20, 20)
        else:
            # Light theme
            self.colors["white_key"] = QColor(245, 246, 248)
            self.colors["black_key"] = QColor(30, 30, 35)
            
        self.update()

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
            color = self.colors["white_key"]
            if note in self.expected_notes:
                color = self.colors["expected"]
            if note in self.held_notes:
                color = self.colors["held"]
            painter.setPen(QPen(self.colors["outline"]))
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)

        # Draw black keys
        for note, x, w in black_keys:
            rect = QRectF(x, 0, w, height * 0.6)
            color = self.colors["black_key"]
            if note in self.expected_notes:
                color = self.colors["expected"].darker(120)
            if note in self.held_notes:
                color = self.colors["held"]
            painter.setPen(QPen(Qt.GlobalColor.black))
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)

