from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Set

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout

from .scoring import ScoreEvent


@dataclass
class FeedbackMessage:
    text: str
    color: QColor
    timestamp: float


class FeedbackPanel(QWidget):
    """Real-time feedback panel showing next expected notes, accuracy meter, combo streaks, and error messages."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setStyleSheet("background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;")
        
        # State
        self.next_expected: Set[int] = set()
        self.recent_scores: deque[ScoreEvent] = deque(maxlen=8)  # Last 8 notes
        self.combo_streak: int = 0
        self.current_bar_score: tuple[int, int] = (0, 0)  # (correct, total)
        self.error_messages: deque[FeedbackMessage] = deque(maxlen=5)  # Last 5 error messages
        
        # UI components
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Next expected chord section
        next_label = QLabel("Next Expected:")
        next_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.next_notes_label = QLabel("--")
        self.next_notes_label.setFont(QFont("Arial", 12))
        self.next_notes_label.setStyleSheet("color: #0ea5e9;")
        
        # Accuracy meter
        acc_label = QLabel("Recent Accuracy:")
        acc_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.accuracy_meter = AccuracyMeter()
        
        # Combo streak
        self.combo_label = QLabel("Combo: 0")
        self.combo_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.combo_label.setStyleSheet("color: #f59e0b;")
        
        # Current bar score
        self.bar_score_label = QLabel("Bar: 0/0")
        self.bar_score_label.setFont(QFont("Arial", 10))
        
        # Error messages
        error_label = QLabel("Feedback:")
        error_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.error_display = QLabel("")
        self.error_display.setWordWrap(True)
        self.error_display.setStyleSheet("color: #dc2626; min-height: 40px;")
        self.error_display.setFont(QFont("Arial", 9))
        
        # Layout
        layout.addWidget(next_label)
        layout.addWidget(self.next_notes_label)
        layout.addWidget(acc_label)
        layout.addWidget(self.accuracy_meter)
        hbox = QHBoxLayout()
        hbox.addWidget(self.combo_label)
        hbox.addWidget(self.bar_score_label)
        layout.addLayout(hbox)
        layout.addWidget(error_label)
        layout.addWidget(self.error_display)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Timer to fade old error messages
        self.fade_timer = QTimer()
        self.fade_timer.timeout.connect(self._update_display)
        self.fade_timer.start(100)  # Update every 100ms

    def set_next_expected(self, notes: Set[int]) -> None:
        """Update the next expected notes/chord."""
        self.next_expected = notes
        if notes:
            note_names = [self._note_name(n) for n in sorted(notes)]
            self.next_notes_label.setText(" ".join(note_names))
        else:
            self.next_notes_label.setText("--")

    def add_score_event(self, event: ScoreEvent) -> None:
        """Add a new score event and update feedback."""
        self.recent_scores.append(event)
        self.accuracy_meter.update_scores(list(self.recent_scores))
        
        # Update combo streak
        if event.verdict == "PERFECT":
            self.combo_streak += 1
        elif event.verdict in ("MISS", "WRONG"):
            self.combo_streak = 0
        
        # Generate error message if needed
        if event.verdict != "PERFECT":
            msg = self._generate_error_message(event)
            if msg:
                self.error_messages.append(FeedbackMessage(
                    text=msg,
                    color=QColor(220, 38, 38),  # Red for errors
                    timestamp=0.0  # Will be set by timer
                ))
        
        self._update_display()

    def update_bar_score(self, correct: int, total: int) -> None:
        """Update the current bar score."""
        self.current_bar_score = (correct, total)
        self.bar_score_label.setText(f"Bar: {correct}/{total}")

    def _generate_error_message(self, event: ScoreEvent) -> Optional[str]:
        """Generate a specific error message from a score event."""
        messages = []
        
        if event.verdict == "LATE":
            ms = abs(event.delta_ms)
            messages.append(f"Late by {ms:.0f}ms")
        elif event.verdict == "EARLY":
            ms = abs(event.delta_ms)
            messages.append(f"Early by {ms:.0f}ms")
        elif event.verdict == "WRONG":
            if event.extra_notes:
                wrong_names = [self._note_name(n) for n in sorted(event.extra_notes)]
                messages.append(f"Wrong notes: {', '.join(wrong_names)}")
        elif event.verdict == "MISS":
            if event.missing_notes:
                missing_names = [self._note_name(n) for n in sorted(event.missing_notes)]
                if len(missing_names) == 1:
                    messages.append(f"Missing: {missing_names[0]}")
                else:
                    messages.append(f"Missing notes: {', '.join(missing_names)}")
        
        if not event.chord_complete and len(event.missing_notes) > 0:
            if len(event.missing_notes) == 1:
                missing_name = self._note_name(list(event.missing_notes)[0])
                if len(event.expected) > 1:
                    messages.append(f"Incomplete chord (missing {missing_name})")
            else:
                messages.append(f"Incomplete chord ({len(event.missing_notes)} notes missing)")
        
        return " | ".join(messages) if messages else None

    def _note_name(self, midi_note: int) -> str:
        """Convert MIDI note number to note name (e.g., 60 -> 'C4')."""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (midi_note // 12) - 1
        note = note_names[midi_note % 12]
        return f"{note}{octave}"

    def _update_display(self) -> None:
        """Update the display with current state."""
        # Update combo label
        if self.combo_streak > 0:
            self.combo_label.setText(f"🔥 Combo: {self.combo_streak} perfect notes!")
            if self.combo_streak > 10:
                self.combo_label.setStyleSheet("color: #f59e0b; font-weight: bold;")
            elif self.combo_streak > 5:
                self.combo_label.setStyleSheet("color: #eab308; font-weight: bold;")
            else:
                self.combo_label.setStyleSheet("color: #84cc16; font-weight: bold;")
        else:
            self.combo_label.setText("Combo: 0")
            self.combo_label.setStyleSheet("color: #6b7280;")
        
        # Update error messages
        if self.error_messages:
            latest = self.error_messages[-1]
            self.error_display.setText(latest.text)
        else:
            self.error_display.setText("")
        
        self.update()


class AccuracyMeter(QWidget):
    """Visual meter showing recent accuracy with colored indicators."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(30)
        self.scores: List[ScoreEvent] = []

    def update_scores(self, scores: List[ScoreEvent]) -> None:
        """Update the scores to display."""
        self.scores = scores
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        """Draw the accuracy meter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        cell_width = width / 8 if len(self.scores) > 0 else width / 8
        
        x = 0
        for i, score in enumerate(self.scores):
            # Determine color based on verdict
            if score.verdict == "PERFECT":
                color = QColor(34, 197, 94)  # Green
            elif score.verdict == "GOOD":
                color = QColor(234, 179, 8)  # Yellow
            elif score.verdict in ("LATE", "EARLY"):
                color = QColor(251, 146, 60)  # Orange
            else:  # MISS, WRONG
                color = QColor(239, 68, 68)  # Red
            
            rect = painter.window()
            cell_rect = rect.adjusted(int(x), 2, int(x + cell_width - 2), -2)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(cell_rect, 3, 3)
            
            # Draw symbol
            symbol = "✓" if score.verdict == "PERFECT" else "○" if score.verdict == "GOOD" else "✗"
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, symbol)
            
            x += cell_width
        
        # Draw empty cells
        for i in range(len(self.scores), 8):
            cell_rect = painter.window().adjusted(int(x), 2, int(x + cell_width - 2), -2)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.setBrush(QBrush(QColor(240, 240, 240)))
            painter.drawRoundedRect(cell_rect, 3, 3)
            x += cell_width


