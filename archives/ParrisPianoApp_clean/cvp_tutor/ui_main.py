from __future__ import annotations

import threading
import time
import webbrowser
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from collections import Counter

import mido
from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from .midi_io import MidiIO
from .midi_parse import parse_midi
from .models import MidiEvent, MidiPart
from .tutor_engine import TutorEngine
from .playback import PlaybackEngine
from .timeline import group_expected
from .performance import PerformanceCapture
from .keyboard_view import KeyboardView
from .piano_roll import PianoRollView
from .scoring import score_performance
from .score_view import ScoreView


def _clamp_note(value: int) -> int:
    return max(0, min(127, value))


class MainWindow(QMainWindow):
    status_changed = pyqtSignal(str)
    expected_changed = pyqtSignal(float, object)  # time_sec, notes set
    score_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CVP Tutor")
        self.resize(1000, 620)
        self.engine = MidiIO()
        self.playback = PlaybackEngine(self.engine)
        self.tutor = TutorEngine()
        self.performance = PerformanceCapture(self.engine)
        self.engine.register_listener(self.on_midi_in)
        self.expected_changed.connect(self.on_expected_changed)
        self.score_changed.connect(self.on_score_changed)
        self.midi_file: Optional[Path] = None
        self.parts: List[MidiPart] = []
        self.events: List[MidiEvent] = []
        self.total_time: float = 0.0
        self.play_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self.loop_start = 0.0
        self.loop_end: Optional[float] = None
        self.learning_channel: Optional[int] = None
        self.learning_track: Optional[int] = None
        self.current_expected: set[int] = set()

        self._build_ui()
        self.status_changed.connect(self._update_status)
        self.refresh_devices(auto_select=True)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(10)

        # Devices
        devices_box = QGroupBox("MIDI Devices")
        d_layout = QGridLayout()
        d_layout.setHorizontalSpacing(8)
        d_layout.setVerticalSpacing(6)
        self.in_combo = QComboBox()
        self.out_combo = QComboBox()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_devices(auto_select=False))
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.connect_devices)
        test_btn = QPushButton("Test Tone")
        test_btn.clicked.connect(self.test_tone)

        d_layout.addWidget(QLabel("Input"), 0, 0)
        d_layout.addWidget(self.in_combo, 0, 1, 1, 2)
        d_layout.addWidget(refresh_btn, 0, 3)
        d_layout.addWidget(test_btn, 0, 4)
        d_layout.addWidget(QLabel("Output"), 1, 0)
        d_layout.addWidget(self.out_combo, 1, 1, 1, 2)
        d_layout.addWidget(connect_btn, 1, 3, 1, 2)
        d_layout.setColumnStretch(1, 2)
        d_layout.setColumnStretch(2, 1)
        d_layout.setColumnStretch(3, 1)
        devices_box.setLayout(d_layout)

        # File controls
        file_box = QGroupBox("Song")
        f_layout = QGridLayout()
        f_layout.setHorizontalSpacing(8)
        f_layout.setVerticalSpacing(6)
        self.file_label = QLabel("No file loaded")
        self.learning_part_combo = QComboBox()
        self.learning_part_combo.currentIndexChanged.connect(self._part_changed)
        open_btn = QPushButton("Open MIDI")
        open_btn.clicked.connect(self.open_file)
        self.sheet_btn = QPushButton("Open Sheet Music Folder")
        self.sheet_btn.clicked.connect(self.open_sheet_music)
        self.export_btn = QPushButton("Export to MusicXML (MuseScore)")
        self.export_btn.clicked.connect(self.export_musicxml)
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.start_playback)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_playback)

        self.tempo_slider = QSlider(Qt.Orientation.Horizontal)
        self.tempo_slider.setMinimum(50)
        self.tempo_slider.setMaximum(125)
        self.tempo_slider.setValue(100)
        self.tempo_label = QLabel("Tempo 1.00x")
        self.tempo_slider.valueChanged.connect(self._tempo_changed)

        self.transpose_slider = QSlider(Qt.Orientation.Horizontal)
        self.transpose_slider.setMinimum(-12)
        self.transpose_slider.setMaximum(12)
        self.transpose_slider.setValue(0)
        self.transpose_label = QLabel("Transpose 0")
        self.transpose_slider.valueChanged.connect(self._transpose_changed)

        self.loop_start_spin = QDoubleSpinBox()
        self.loop_start_spin.setRange(0, 3600)
        self.loop_start_spin.setDecimals(2)
        self.loop_end_spin = QDoubleSpinBox()
        self.loop_end_spin.setRange(0, 3600)
        self.loop_end_spin.setDecimals(2)
        self.loop_end_spin.setSpecialValueText("0 = end")
        loop_label = QLabel("Loop start/end (s)")

        self.tutor_toggle = QCheckBox("Tutor (wait for you to play Learning Part)")
        self.tutor_toggle.setChecked(True)

        f_layout.addWidget(open_btn, 0, 0)
        f_layout.addWidget(self.file_label, 0, 1, 1, 3)

        f_layout.addWidget(self.sheet_btn, 1, 0)
        f_layout.addWidget(self.export_btn, 1, 1)
        f_layout.addWidget(QLabel("Learning Part"), 1, 2)
        f_layout.addWidget(self.learning_part_combo, 1, 3)

        f_layout.addWidget(self.play_btn, 2, 0)
        f_layout.addWidget(self.stop_btn, 2, 1)
        f_layout.addWidget(self.tutor_toggle, 2, 2, 1, 2)

        f_layout.addWidget(self.tempo_label, 3, 0)
        f_layout.addWidget(self.tempo_slider, 3, 1, 1, 3)

        f_layout.addWidget(self.transpose_label, 4, 0)
        f_layout.addWidget(self.transpose_slider, 4, 1, 1, 3)

        f_layout.addWidget(loop_label, 5, 0)
        f_layout.addWidget(self.loop_start_spin, 5, 1)
        f_layout.addWidget(self.loop_end_spin, 5, 2)
        f_layout.setColumnStretch(1, 1)
        f_layout.setColumnStretch(2, 1)
        f_layout.setColumnStretch(3, 1)
        file_box.setLayout(f_layout)

        tabs = QTabWidget()
        self.keyboard = KeyboardView()
        self.keyboard.setStyleSheet("background: #f7f7f7; border: 1px solid #d0d0d0;")
        self.roll = PianoRollView()
        self.score = ScoreView()
        tabs.addTab(self.keyboard, "Keyboard")
        tabs.addTab(self.roll, "Piano Roll")
        tabs.addTab(self.score, "Score")
        layout.addWidget(tabs)

        # Status
        self.status = QLabel("Ready")
        self.score_label = QLabel("Score: --")
        layout.addWidget(devices_box)
        layout.addWidget(file_box)
        layout.addWidget(self.status)
        layout.addWidget(self.score_label)
        root.setLayout(layout)
        self.setCentralWidget(root)

    def refresh_devices(self, auto_select: bool = True) -> None:
        self.in_combo.clear()
        self.out_combo.clear()
        inputs = self.engine.list_inputs()
        outputs = self.engine.list_outputs()
        self.in_combo.addItems(inputs)
        self.out_combo.addItems(outputs)
        if auto_select:
            self._auto_select(inputs, outputs)

    def _auto_select(self, inputs: List[str], outputs: List[str]) -> None:
        def pick(names: List[str]) -> int:
            for i, name in enumerate(names):
                if "CVP-301" in name or "Yamaha" in name:
                    return i
            return 0 if names else -1

        in_idx = pick(inputs)
        out_idx = pick(outputs)
        if in_idx >= 0:
            self.in_combo.setCurrentIndex(in_idx)
        if out_idx >= 0:
            self.out_combo.setCurrentIndex(out_idx)

    def connect_devices(self) -> None:
        input_name = self.in_combo.currentText() or None
        output_name = self.out_combo.currentText() or None
        self.engine.open(input_name, output_name)
        self.status.setText(f"Connected IN={input_name or 'None'} OUT={output_name or 'None'}")

    def test_tone(self) -> None:
        ch = 0
        self.engine.send_test_tone(channel=ch)

    def open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Open MIDI", "", "MIDI Files (*.mid *.midi)")
        if not file_path:
            return
        self.load_file(Path(file_path))

    def load_file(self, path: Path) -> None:
        self.midi_file = path
        self.parts, self.events, self.total_time = parse_midi(path)
        self.performance.reset()
        count = self.roll.load_notes(self.events, self.learning_channel, self.learning_track, self.total_time, show_all=True)
        self.render_score_pdf()
        self.file_label.setText(f"{path.name} ({self.total_time:.1f}s)")
        self.status.setText(f"Loaded {count} notes into Piano Roll")
        self.learning_part_combo.clear()
        for idx, part in enumerate(self.parts):
            ch = f"ch {part.channel}" if part.channel is not None else "ch ?"
            self.learning_part_combo.addItem(f"{idx}: {part.name} ({ch}) notes={part.note_count}", userData=part)
        if self.parts:
            self.learning_part_combo.setCurrentIndex(0)
            self._part_changed(0)

    def _part_changed(self, index: int) -> None:
        part: MidiPart = self.learning_part_combo.itemData(index)
        if not part:
            return
        self.learning_channel = part.channel
        self.learning_track = part.track_index
        self.current_expected = set()
        self.keyboard.set_expected(set())
        if self.midi_file:
            count = self.roll.load_notes(self.events, self.learning_channel, self.learning_track, self.total_time, show_all=True)
            self.status.setText(f"Piano Roll notes: {count}")
            self.render_score_pdf()

    def open_sheet_music(self) -> None:
        url = "https://drive.google.com/drive/folders/0B6bODXWhwMjKdDU3U1p3bjFmLTA?resourcekey=0-aQ1yhQwnHbthIVjs5_ry_g&usp=sharing"
        webbrowser.open(url)
        self.status.setText("Opened sheet music folder.")

    def _find_musescore(self) -> Optional[str]:
        candidates = [
            "C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe",
            "C:\\Program Files\\MuseScore 3\\bin\\MuseScore3.exe",
            shutil.which("MuseScore4.exe"),
            shutil.which("MuseScore3.exe"),
            shutil.which("MuseScore.exe"),
        ]
        for c in candidates:
            if c and Path(c).exists():
                return c
        return None

    def export_musicxml(self) -> None:
        if not self.midi_file:
            self.status.setText("Open a MIDI file first.")
            return
        exe = self._find_musescore()
        if not exe:
            self.status.setText("MuseScore not found. Install MuseScore 3/4 to export.")
            return
        out_path = self.midi_file.with_suffix(".musicxml")
        try:
            subprocess.run([exe, "-o", str(out_path), str(self.midi_file)], check=True)
            self.status.setText(f"Exported MusicXML: {out_path.name}")
        except Exception as exc:
            self.status.setText(f"Export failed: {exc}")

    def render_score_pdf(self) -> None:
        """Export MIDI to PDF via MuseScore and load in Score tab."""
        if not self.midi_file:
            return
        exe = self._find_musescore()
        if not exe:
            self.score.label.setText("MuseScore not found. Install MuseScore 3/4 for notation.")
            return
        pdf_path = self.midi_file.with_suffix(".pdf")
        try:
            subprocess.run([exe, "-o", str(pdf_path), str(self.midi_file)], check=True)
            self.score.load_pdf(pdf_path)
            self.status.setText(f"Score rendered (opens externally): {pdf_path.name}")
        except Exception as exc:
            self.score.label.setText(f"Score export failed: {exc}")

    def _tempo_changed(self, value: int) -> None:
        self.tempo_label.setText(f"Tempo {value/100:.2f}x")

    def _transpose_changed(self, value: int) -> None:
        self.transpose_label.setText(f"Transpose {value:+d}")

    def start_playback(self) -> None:
        if not self.events:
            self.status.setText("Load a MIDI file first.")
            return
        if self.play_thread and self.play_thread.is_alive():
            self.status.setText("Already playing.")
            return
        self.performance.reset()
        tempo_mult = self.tempo_slider.value() / 100.0
        transpose = self.transpose_slider.value()
        loop_start = self.loop_start_spin.value()
        loop_end = self.loop_end_spin.value() or None
        tutor_on = self.tutor_toggle.isChecked()
        chords = []
        if tutor_on:
            chords = group_expected(self.events, self.learning_channel, self.learning_track)
            self.current_expected = chords[0].notes if chords else set()
            self.keyboard.set_expected(self.current_expected)
            self.expected_changed.emit(chords[0].time if chords else 0.0, self.current_expected)
        else:
            chords = group_expected(self.events, self.learning_channel, self.learning_track)
        self.stop_flag.clear()
        self.play_thread = threading.Thread(
            target=self._playback_loop,
            args=(tempo_mult, transpose, loop_start, loop_end, tutor_on, chords),
            daemon=True,
        )
        self.play_thread.start()

    def stop_playback(self) -> None:
        self.stop_flag.set()
        self.status.setText("Stopped.")

    def _playback_loop(self, tempo_mult: float, transpose: int, loop_start: float, loop_end: Optional[float], tutor_on: bool, chords) -> None:
        chord_idx = 0
        start_wall = time.perf_counter()
        for ev in self.events:
            if self.stop_flag.is_set():
                break
            if ev.time < loop_start:
                continue
            if loop_end and ev.time > loop_end:
                break
            target_time = start_wall + (ev.time - loop_start) / tempo_mult
            while not self.stop_flag.is_set() and time.perf_counter() < target_time:
                time.sleep(0.001)
            msg = ev.message.copy()
            if msg.type in {"note_on", "note_off"} and transpose:
                msg.note = _clamp_note(msg.note + transpose)
            is_learning_part = (self.learning_channel is None or msg.channel == self.learning_channel) and (
                self.learning_track is None or ev.track_index == self.learning_track
            )
            if tutor_on and is_learning_part and msg.type == "note_on" and chord_idx < len(chords):
                expected = chords[chord_idx]
                chord_idx += 1
                self.current_expected = expected.notes
                self.status_changed.emit(f"Next: {sorted(expected.notes)}")
                self.keyboard.set_expected(self.current_expected)
                self.expected_changed.emit(expected.time, expected.notes)
                matched = self.engine.wait_for_notes(expected.notes, timeout=10, strict=self.tutor.strict)
                status = "matched" if matched else "timeout"
                self.status_changed.emit(f"Tutor: expected {expected.notes} -> {status}")
                self.current_expected = set()
                self.keyboard.set_expected(set())
                continue
            self.engine.send(msg)
        self.status_changed.emit("Playback finished.")
        if chords:
            results = score_performance(chords, self.performance.events)
            counts = Counter(r.verdict for r in results)
            total = len(results)
            summary = f"Score: Perfect={counts.get('PERFECT',0)} Good={counts.get('GOOD',0)} Miss={counts.get('MISS',0)} / {total}"
            self.score_changed.emit(summary)

    def _update_status(self, text: str) -> None:
        self.status.setText(text)
        # Update held keys on MIDI input
        # (PerformanceCapture already collects; here we only track current pressed)
        # This runs in UI thread from signal; for simplicity the held state is set by incoming listener below.

    def on_midi_in(self, msg: mido.Message) -> None:
        if msg.type == "note_on" and msg.velocity > 0:
            self.keyboard.held_notes.add(msg.note)
        elif msg.type in {"note_off", "note_on"}:
            try:
                self.keyboard.held_notes.remove(msg.note)
            except KeyError:
                pass
        self.keyboard.update()

    def on_expected_changed(self, time_sec: float, notes: set[int]) -> None:
        self.roll.highlight_expected(notes, time_sec)

    def on_score_changed(self, text: str) -> None:
        self.score_label.setText(text)


def run() -> None:
    logger.info("Starting CVP Tutor UI")
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":  # pragma: no cover
    run()
