from __future__ import annotations

from pathlib import Path
import webbrowser
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class ScoreView(QWidget):
    """Embeds a PDF score via WebEngine."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.label = QLabel("Score will open externally (PDF).")
        self.button = QPushButton("Open latest score")
        self.button.setEnabled(False)
        self.button.clicked.connect(self.open_external)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.last_pdf: Path | None = None

    def load_pdf(self, path: Path) -> None:
        if not path.exists():
            self.label.setText("Score PDF not found.")
            self.button.setEnabled(False)
            return
        self.last_pdf = path
        self.button.setEnabled(True)
        self.label.setText(f"Score ready: {path.name} (opens externally)")
        self.open_external()

    def open_external(self) -> None:
        if self.last_pdf and self.last_pdf.exists():
            webbrowser.open(self.last_pdf.as_uri())
