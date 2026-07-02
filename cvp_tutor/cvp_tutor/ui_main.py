from __future__ import annotations

import json
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
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSignal
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
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from .midi_io import MidiIO
from .midi_parse import build_barlines, build_time_signatures, parse_midi
from .models import MidiEvent, MidiPart
from .playback import shift_start_for_pause
from .tutor_engine import TutorEngine
from .playback import PlaybackEngine, track_is_playable
from .timeline import group_expected
from .performance import PerformanceCapture
from .keyboard_view import KeyboardView
from .notation_roll import NotationRollView, build_rendered_notes
from .piano_roll import PianoRollView
from .progression import (
    SessionProgress,
    calculate_session_progress,
    level_for_total_xp,
    live_xp_for_notes,
    xp_required_for_level,
)
from .scoring import score_performance
from .score_view import ScoreView
from .settings_store import SettingsStore


def _clamp_note(value: int) -> int:
    return max(0, min(127, value))


def _format_clock(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def _playback_meter_text(current_time: float, total_time: float, next_cue_time: Optional[float], waiting_for_input: bool) -> str:
    base = f"Song Time: {_format_clock(current_time)} / {_format_clock(total_time)}"
    if total_time <= 0:
        return base
    if waiting_for_input:
        return f"{base} | Next cue: play now"
    if next_cue_time is None:
        return f"{base} | Next cue: --"
    delta = max(0.0, next_cue_time - current_time)
    return f"{base} | Next cue in {delta:.1f}s"


class CollapsibleSection(QWidget):
    def __init__(self, title: str, body: QWidget, expanded: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.clicked.connect(self._apply_state)
        self.body = body

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.toggle)
        layout.addWidget(self.body)
        self.setLayout(layout)
        self._apply_state()

    def _apply_state(self) -> None:
        expanded = self.toggle.isChecked()
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.body.setVisible(expanded)

    def is_expanded(self) -> bool:
        return self.toggle.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        self.toggle.setChecked(expanded)
        self._apply_state()


class MainWindow(QMainWindow):
    status_changed = pyqtSignal(str)
    expected_changed = pyqtSignal(float, object)  # time_sec, notes set
    score_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(str)

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
        self.progress_changed.connect(self.on_progress_changed)
        self.midi_file: Optional[Path] = None
        self.parts: List[MidiPart] = []
        self.events: List[MidiEvent] = []
        self.total_time: float = 0.0
        self.barlines: List[float] = []
        self.time_signatures: List[tuple[float, int, int]] = []
        self.play_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self.loop_start = 0.0
        self.loop_end: Optional[float] = None
        self.learning_channel: Optional[int] = None
        self.learning_track: Optional[int] = None
        self.current_expected: set[int] = set()
        self.last_score_results = []
        self.last_score_summary = "Score: --"
        self.total_xp = 0
        self.last_progress: Optional[SessionProgress] = None
        self.run_start_total_xp = 0
        self.live_session_xp = 0
        self._progress_anim: Optional[QPropertyAnimation] = None
        self._progress_flash_timer = QTimer(self)
        self._progress_flash_timer.setSingleShot(True)
        self._progress_flash_timer.timeout.connect(self._clear_progress_bar_flash)
        self._progress_level = 1
        self._progress_bar_maximum = 100
        self.playback_position_sec = 0.0
        self.next_cue_time_sec: Optional[float] = None
        self.next_cue_notes: set[int] = set()
        self.waiting_for_input = False
        self.playback_active = False
        self.playback_meter_timer = QTimer(self)
        self.playback_meter_timer.setInterval(100)
        self.playback_meter_timer.timeout.connect(self._update_playback_meter)
        self.settings = SettingsStore()

        self._build_ui()
        self.status_changed.connect(self._update_status)
        self.refresh_devices(auto_select=True)
        self._update_playback_meter()
        self._restore_ui_preferences()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(10)

        # View controls
        view_box = QGroupBox("View")
        view_layout = QHBoxLayout()
        view_layout.setSpacing(12)
        self.view_toggles: dict[str, QCheckBox] = {}
        self.section_widgets: dict[str, QWidget] = {}
        for key, label in (
            ("midi_devices", "Show MIDI Devices"),
            ("song", "Show Song"),
            ("keyboard_tabs", "Show Keyboard / Roll / Score"),
            ("status", "Show Status"),
            ("song_meter", "Show Song Timer"),
            ("xp", "Show XP"),
        ):
            toggle = QCheckBox(label)
            toggle.setChecked(True)
            self.view_toggles[key] = toggle
            view_layout.addWidget(toggle)
        view_layout.addStretch(1)
        view_box.setLayout(view_layout)

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

        file_box = QGroupBox("Song")
        file_box_layout = QVBoxLayout()
        file_box_layout.setContentsMargins(10, 10, 10, 10)
        file_box_layout.setSpacing(10)
        self.file_label = QLabel("No file loaded")
        self.learning_part_combo = QComboBox()
        self.learning_part_combo.currentIndexChanged.connect(self._part_changed)
        mixer_actions = QWidget()
        mixer_actions_layout = QHBoxLayout()
        mixer_actions_layout.setContentsMargins(0, 0, 0, 0)
        mixer_actions_layout.setSpacing(8)
        self.mute_all_btn = QPushButton("Mute All")
        self.mute_all_btn.clicked.connect(self._mute_all_tracks)
        self.unmute_all_btn = QPushButton("Unmute All")
        self.unmute_all_btn.clicked.connect(self._unmute_all_tracks)
        self.clear_solo_btn = QPushButton("Clear Solo")
        self.clear_solo_btn.clicked.connect(self._clear_track_solos)
        self.solo_learning_btn = QPushButton("Solo Learning Part")
        self.solo_learning_btn.clicked.connect(self._solo_learning_part)
        mixer_actions_layout.addWidget(self.mute_all_btn)
        mixer_actions_layout.addWidget(self.unmute_all_btn)
        mixer_actions_layout.addWidget(self.clear_solo_btn)
        mixer_actions_layout.addWidget(self.solo_learning_btn)
        mixer_actions_layout.addStretch(1)
        mixer_actions.setLayout(mixer_actions_layout)
        self.track_controls_container = QWidget()
        self.track_controls_layout = QVBoxLayout()
        self.track_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.track_controls_layout.setSpacing(6)
        self.track_controls_container.setLayout(self.track_controls_layout)
        self.track_controls_scroll = QScrollArea()
        self.track_controls_scroll.setWidgetResizable(True)
        self.track_controls_scroll.setMinimumHeight(120)
        self.track_controls_scroll.setWidget(self.track_controls_container)
        self.track_row_widgets: dict[int, QWidget] = {}
        open_btn = QPushButton("Open MIDI")
        open_btn.clicked.connect(self.open_file)
        self.sheet_btn = QPushButton("Open Sheet Music Folder")
        self.sheet_btn.clicked.connect(self.open_sheet_music)
        self.export_btn = QPushButton("Export to MusicXML (MuseScore)")
        self.export_btn.clicked.connect(self.export_musicxml)
        self.export_session_btn = QPushButton("Export Session Summary")
        self.export_session_btn.clicked.connect(self.export_session_summary)
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

        file_body = QWidget()
        file_layout = QGridLayout()
        file_layout.setHorizontalSpacing(8)
        file_layout.setVerticalSpacing(6)
        file_layout.addWidget(open_btn, 0, 0)
        file_layout.addWidget(self.file_label, 0, 1, 1, 3)
        file_layout.addWidget(self.sheet_btn, 1, 0)
        file_layout.addWidget(self.export_btn, 1, 1)
        file_layout.addWidget(self.export_session_btn, 1, 2)
        file_layout.setColumnStretch(1, 1)
        file_layout.setColumnStretch(2, 1)
        file_body.setLayout(file_layout)

        playback_body = QWidget()
        playback_layout = QGridLayout()
        playback_layout.setHorizontalSpacing(8)
        playback_layout.setVerticalSpacing(6)
        playback_layout.addWidget(self.play_btn, 0, 0)
        playback_layout.addWidget(self.stop_btn, 0, 1)
        playback_layout.addWidget(self.tempo_label, 1, 0)
        playback_layout.addWidget(self.tempo_slider, 1, 1, 1, 3)
        playback_layout.addWidget(self.transpose_label, 2, 0)
        playback_layout.addWidget(self.transpose_slider, 2, 1, 1, 3)
        playback_layout.addWidget(loop_label, 3, 0)
        playback_layout.addWidget(self.loop_start_spin, 3, 1)
        playback_layout.addWidget(self.loop_end_spin, 3, 2)
        playback_body.setLayout(playback_layout)

        tutor_body = QWidget()
        tutor_layout = QGridLayout()
        tutor_layout.setHorizontalSpacing(8)
        tutor_layout.setVerticalSpacing(6)
        tutor_layout.addWidget(QLabel("Learning Part"), 0, 0)
        tutor_layout.addWidget(self.learning_part_combo, 0, 1)
        tutor_layout.addWidget(self.tutor_toggle, 1, 0, 1, 2)
        tutor_body.setLayout(tutor_layout)

        mixer_body = QWidget()
        mixer_layout = QVBoxLayout()
        mixer_layout.setContentsMargins(0, 0, 0, 0)
        mixer_layout.setSpacing(6)
        mixer_layout.addWidget(mixer_actions)
        mixer_layout.addWidget(self.track_controls_scroll)
        mixer_body.setLayout(mixer_layout)

        self.song_sections = {
            "file": CollapsibleSection("File", file_body, expanded=True),
            "playback": CollapsibleSection("Playback", playback_body, expanded=True),
            "tutor": CollapsibleSection("Tutor", tutor_body, expanded=True),
            "mixer": CollapsibleSection("Track Mixer", mixer_body, expanded=True),
        }
        for key, section in self.song_sections.items():
            section.toggle.clicked.connect(self._save_ui_preferences)
            file_box_layout.addWidget(section)
        file_box_layout.addStretch(1)
        file_box.setLayout(file_box_layout)

        tabs = QTabWidget()
        self.keyboard = KeyboardView()
        self.keyboard.setStyleSheet("background: #f7f7f7; border: 1px solid #d0d0d0;")
        self.roll = PianoRollView()
        self.notation = NotationRollView()
        self.score = ScoreView()
        keyboard_tab = QWidget()
        keyboard_layout = QVBoxLayout()
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard_layout.setSpacing(8)
        keyboard_layout.addWidget(self.keyboard, 0)
        keyboard_layout.addWidget(self.notation, 1)
        keyboard_tab.setLayout(keyboard_layout)
        tabs.addTab(keyboard_tab, "Keyboard")
        tabs.addTab(self.roll, "Piano Roll")
        tabs.addTab(self.score, "Score")
        tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Status
        self.status = QLabel("Ready")
        self.score_label = QLabel("Score: --")
        self.playback_meter_label = QLabel("Song Time: 00:00 / 00:00 | Next cue: --")
        self.progress_label = QLabel("Adventure XP: 0 | Level 1")
        self.progress_bar = QProgressBar()
        self.song_progress_bar = QProgressBar()
        self.song_progress_bar.setRange(0, 1000)
        self.song_progress_bar.setValue(0)
        self.song_progress_bar.setFormat("Song progress")
        self.song_progress_bar.setTextVisible(False)
        self.song_progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #9ca3af;
                border-radius: 5px;
                background: #e5e7eb;
                height: 14px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #059669);
            }
            """
        )
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Level 1: 0 / 100 XP")
        self.progress_bar.setTextVisible(True)
        self._apply_progress_bar_style()

        status_box = QGroupBox("Status")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(10, 8, 10, 10)
        status_layout.addWidget(self.status)
        status_layout.addWidget(self.score_label)
        status_box.setLayout(status_layout)

        song_meter_box = QGroupBox("Song Timer")
        song_meter_layout = QVBoxLayout()
        song_meter_layout.setContentsMargins(10, 8, 10, 10)
        song_meter_layout.addWidget(self.playback_meter_label)
        song_meter_layout.addWidget(self.song_progress_bar)
        song_meter_box.setLayout(song_meter_layout)

        xp_box = QGroupBox("Progress")
        xp_layout = QVBoxLayout()
        xp_layout.setContentsMargins(10, 8, 10, 10)
        xp_layout.addWidget(self.progress_bar)
        xp_layout.addWidget(self.progress_label)
        xp_box.setLayout(xp_layout)
        self.xp_popup = QLabel("+10 XP", xp_box)
        self.xp_popup.hide()
        self.xp_popup.setStyleSheet(
            "QLabel { background: rgba(15,23,42,220); color: #f8fafc; border: 1px solid #60a5fa; "
            "border-radius: 8px; padding: 4px 10px; font-weight: 700; }"
        )
        self.xp_popup.raise_()
        self.xp_popup_timer = QTimer(self)
        self.xp_popup_timer.setSingleShot(True)
        self.xp_popup_timer.timeout.connect(self.xp_popup.hide)

        controls_column = QWidget()
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)
        controls_layout.addWidget(view_box)
        controls_layout.addWidget(devices_box)
        controls_layout.addWidget(file_box)
        controls_layout.addStretch(1)
        controls_column.setLayout(controls_layout)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        controls_scroll.setWidget(controls_column)
        controls_scroll.setMinimumWidth(460)

        info_row = QWidget()
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)
        info_layout.addWidget(status_box, 1)
        info_layout.addWidget(song_meter_box, 2)
        info_layout.addWidget(xp_box, 2)
        info_row.setLayout(info_layout)

        main_right = QWidget()
        main_right_layout = QVBoxLayout()
        main_right_layout.setContentsMargins(0, 0, 0, 0)
        main_right_layout.setSpacing(10)
        main_right_layout.addWidget(tabs, 1)
        main_right_layout.addWidget(info_row, 0)
        main_right.setLayout(main_right_layout)

        workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        workspace_splitter.addWidget(controls_scroll)
        workspace_splitter.addWidget(main_right)
        workspace_splitter.setChildrenCollapsible(False)
        workspace_splitter.setStretchFactor(0, 0)
        workspace_splitter.setStretchFactor(1, 1)
        workspace_splitter.setSizes([520, 1080])

        self.section_widgets = {
            "midi_devices": devices_box,
            "song": file_box,
            "keyboard_tabs": tabs,
            "status": status_box,
            "song_meter": song_meter_box,
            "xp": xp_box,
        }
        for key, toggle in self.view_toggles.items():
            toggle.toggled.connect(lambda checked, section=key: self._on_section_toggle(section, checked))

        layout.addWidget(workspace_splitter, 1)
        root.setLayout(layout)
        self.setCentralWidget(root)

    def _set_section_visible(self, section: str, visible: bool) -> None:
        widget = self.section_widgets.get(section)
        if widget is not None:
            widget.setVisible(visible)

    def _on_section_toggle(self, section: str, visible: bool) -> None:
        self._set_section_visible(section, visible)
        self._save_ui_preferences()

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
        try:
            self.engine.open(input_name, output_name)
            self.status.setText(f"Connected IN={input_name or 'None'} OUT={output_name or 'None'}")
        except RuntimeError as exc:
            self.status.setText(str(exc))

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
        self.barlines = build_barlines(path)
        self.time_signatures = build_time_signatures(path)
        self._load_track_preferences()
        self._rebuild_track_controls()
        self.last_score_results = []
        self.last_score_summary = "Score: --"
        self.score_label.setText(self.last_score_summary)
        self.last_progress = None
        self.live_session_xp = 0
        self.performance.reset()
        self.playback_position_sec = 0.0
        self.next_cue_time_sec = None
        self.next_cue_notes = set()
        self.waiting_for_input = False
        self.playback_active = False
        self._refresh_progress_label()
        self._update_playback_meter()
        count = self.roll.load_notes(self.events, self.learning_channel, self.learning_track, self.total_time, show_all=True)
        self.render_score_pdf()
        self.file_label.setText(f"{path.name} ({self.total_time:.1f}s)")
        self.status.setText(f"Loaded {count} notes into Piano Roll")
        self.learning_part_combo.clear()
        for idx, part in enumerate(self.parts):
            ch = f"ch {part.channel}" if part.channel is not None else "ch ?"
            self.learning_part_combo.addItem(f"{idx}: {part.name} ({ch}) notes={part.note_count}", userData=part)
        if self.parts:
            default_index = next((idx for idx, part in enumerate(self.parts) if part.note_count > 0), 0)
            self.learning_part_combo.setCurrentIndex(default_index)
            self._part_changed(default_index)

    def _part_changed(self, index: int) -> None:
        part: MidiPart = self.learning_part_combo.itemData(index)
        if not part:
            return
        self.learning_channel = part.channel
        self.learning_track = part.track_index
        self.current_expected = set()
        self.keyboard.set_expected(set())
        self.keyboard.set_upcoming(set(), 0.0)
        if self.midi_file:
            count = self.roll.load_notes(self.events, self.learning_channel, self.learning_track, self.total_time, show_all=True)
            self.notation.load_score(
                build_rendered_notes(self.events, self.learning_channel, self.learning_track),
                self.total_time,
                self.barlines,
                self.time_signatures,
            )
            self.status.setText(f"Piano Roll notes: {count}")
            self.render_score_pdf()

    def _rebuild_track_controls(self) -> None:
        while self.track_controls_layout.count():
            item = self.track_controls_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.track_row_widgets.clear()
        if not self.parts:
            empty = QLabel("Load a MIDI file to manage tracks.")
            self.track_controls_layout.addWidget(empty)
            return

        for part in self.parts:
            row = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(6, 2, 6, 2)
            row_layout.setSpacing(10)

            label = QLabel(f"{part.track_index}: {part.name} ({'ch ' + str(part.channel) if part.channel is not None else 'ch ?'}) notes={part.note_count}")
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            mute = QCheckBox("Mute")
            mute.setChecked(part.muted)
            mute.toggled.connect(lambda checked, track=part.track_index: self._set_track_muted(track, checked))
            solo = QCheckBox("Solo")
            solo.setChecked(part.solo)
            solo.toggled.connect(lambda checked, track=part.track_index: self._set_track_solo(track, checked))

            row_layout.addWidget(label, 1)
            row_layout.addWidget(mute)
            row_layout.addWidget(solo)
            row.setLayout(row_layout)
            self.track_controls_layout.addWidget(row)
            self.track_row_widgets[part.track_index] = row

        self.track_controls_layout.addStretch(1)
        self._sync_playback_track_state()

    def _set_track_muted(self, track_index: int, muted: bool) -> None:
        for part in self.parts:
            if part.track_index == track_index:
                part.muted = muted
                break
        self._sync_playback_track_state()
        self._save_track_preferences()

    def _set_track_solo(self, track_index: int, solo: bool) -> None:
        for part in self.parts:
            if part.track_index == track_index:
                part.solo = solo
                break
        self._sync_playback_track_state()
        self._save_track_preferences()

    def _refresh_track_control_checks(self) -> None:
        for row in self.track_row_widgets.values():
            for checkbox in row.findChildren(QCheckBox):
                checkbox.blockSignals(True)
                track_text = checkbox.text()
                parent_layout = row.layout()
                if parent_layout is None:
                    checkbox.blockSignals(False)
                    continue
                label_widget = parent_layout.itemAt(0).widget()
                if not isinstance(label_widget, QLabel):
                    checkbox.blockSignals(False)
                    continue
                track_index = int(label_widget.text().split(":", 1)[0])
                part = next((p for p in self.parts if p.track_index == track_index), None)
                if part is not None:
                    if track_text == "Mute":
                        checkbox.setChecked(part.muted)
                    elif track_text == "Solo":
                        checkbox.setChecked(part.solo)
                checkbox.blockSignals(False)

    def _sync_playback_track_state(self) -> None:
        self.playback.muted_tracks = {part.track_index for part in self.parts if part.muted}
        self.playback.solo_tracks = {part.track_index for part in self.parts if part.solo}

    def _mute_all_tracks(self) -> None:
        for part in self.parts:
            part.muted = True
        self._refresh_track_control_checks()
        self._sync_playback_track_state()
        self._save_track_preferences()

    def _unmute_all_tracks(self) -> None:
        for part in self.parts:
            part.muted = False
        self._refresh_track_control_checks()
        self._sync_playback_track_state()
        self._save_track_preferences()

    def _clear_track_solos(self) -> None:
        for part in self.parts:
            part.solo = False
        self._refresh_track_control_checks()
        self._sync_playback_track_state()
        self._save_track_preferences()

    def _solo_learning_part(self) -> None:
        if self.learning_track is None:
            return
        for part in self.parts:
            part.solo = part.track_index == self.learning_track
        self._refresh_track_control_checks()
        self._sync_playback_track_state()
        self._save_track_preferences()

    def _load_track_preferences(self) -> None:
        if not self.midi_file:
            return
        prefs = self.settings.get_track_preferences(str(self.midi_file.resolve()))
        muted_tracks = {int(track) for track in prefs.get("muted_tracks", [])}
        solo_tracks = {int(track) for track in prefs.get("solo_tracks", [])}
        for part in self.parts:
            part.muted = part.track_index in muted_tracks
            part.solo = part.track_index in solo_tracks
        self._sync_playback_track_state()

    def _save_track_preferences(self) -> None:
        if not self.midi_file:
            return
        payload = {
            "muted_tracks": sorted(part.track_index for part in self.parts if part.muted),
            "solo_tracks": sorted(part.track_index for part in self.parts if part.solo),
        }
        self.settings.set_track_preferences(str(self.midi_file.resolve()), payload)

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
        self._sync_playback_track_state()
        self.last_score_results = []
        self.last_score_summary = "Score: --"
        self.score_label.setText(self.last_score_summary)
        self.last_progress = None
        self.run_start_total_xp = self.total_xp
        self.live_session_xp = 0
        tempo_mult = self.tempo_slider.value() / 100.0
        transpose = self.transpose_slider.value()
        loop_start = self.loop_start_spin.value()
        loop_end = self.loop_end_spin.value() or None
        self.playback_position_sec = loop_start
        self.waiting_for_input = False
        self.playback_active = True
        self.playback_meter_timer.start()
        self._refresh_progress_label()
        tutor_on = self.tutor_toggle.isChecked()
        chords = []
        if tutor_on:
            chords = group_expected(self.events, self.learning_channel, self.learning_track)
            self.current_expected = chords[0].notes if chords else set()
            self.next_cue_time_sec = chords[0].time if chords else None
            self.next_cue_notes = set(chords[0].notes) if chords else set()
            self.keyboard.set_expected(self.current_expected)
            self.expected_changed.emit(chords[0].time if chords else 0.0, self.current_expected)
        else:
            chords = group_expected(self.events, self.learning_channel, self.learning_track)
            self.next_cue_time_sec = None
            self.next_cue_notes = set()
        self.stop_flag.clear()
        self.play_thread = threading.Thread(
            target=self._playback_loop,
            args=(tempo_mult, transpose, loop_start, loop_end, tutor_on, chords),
            daemon=True,
        )
        self.play_thread.start()

    def stop_playback(self) -> None:
        self.stop_flag.set()
        self.current_expected = set()
        self.expected_changed.emit(0.0, set())
        self.keyboard.set_upcoming(set(), 0.0)
        self.notation.highlight_expected(set())
        self.engine.all_notes_off()
        self.playback_active = False
        self.waiting_for_input = False
        self.playback_meter_timer.stop()
        self.next_cue_time_sec = None
        self.next_cue_notes = set()
        self._update_playback_meter()
        self.status.setText("Stopped.")

    def export_session_summary(self) -> None:
        if not self.midi_file:
            self.status.setText("Load a MIDI file before exporting a session summary.")
            return

        suggested = self.midi_file.with_name(f"{self.midi_file.stem}-session-summary.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Session Summary",
            str(suggested),
            "JSON Files (*.json)",
        )
        if not file_path:
            return

        verdict_counts = Counter(result.verdict for result in self.last_score_results)
        payload = {
            "midi_file": str(self.midi_file),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "song_length_seconds": round(self.total_time, 3),
            "learning_track": self.learning_track,
            "learning_channel": self.learning_channel,
            "tempo_multiplier": round(self.tempo_slider.value() / 100.0, 2),
            "transpose": self.transpose_slider.value(),
            "loop_start_seconds": round(self.loop_start_spin.value(), 2),
            "loop_end_seconds": round(self.loop_end_spin.value(), 2),
            "tutor_mode": self.tutor_toggle.isChecked(),
            "score_summary": self.last_score_summary,
            "score_counts": dict(verdict_counts),
            "progression": (
                {
                    "notes_hit": self.last_progress.notes_hit,
                    "perfect_moments": self.last_progress.perfect_moments,
                    "good_moments": self.last_progress.good_moments,
                    "miss_moments": self.last_progress.miss_moments,
                    "xp_earned": self.last_progress.xp_earned,
                    "total_xp": self.last_progress.total_xp,
                    "level": self.last_progress.level,
                    "xp_into_level": self.last_progress.xp_into_level,
                    "xp_to_next_level": self.last_progress.xp_to_next_level,
                }
                if self.last_progress
                else None
            ),
            "score_results": [
                {
                    "expected": sorted(result.expected),
                    "played": sorted(result.played),
                    "matched": sorted(result.matched),
                    "delta_ms": round(result.delta_ms, 2),
                    "verdict": result.verdict,
                }
                for result in self.last_score_results
            ],
        }

        Path(file_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.status.setText(f"Session summary exported: {Path(file_path).name}")

    def _award_live_xp(self, note_count: int) -> None:
        gained = live_xp_for_notes(note_count)
        if gained <= 0:
            return
        self.live_session_xp += gained
        self.total_xp = self.run_start_total_xp + self.live_session_xp
        self._show_xp_popup(gained)
        self._refresh_progress_label()

    def _show_xp_popup(self, gained: int) -> None:
        self.xp_popup.setText(f"+{gained} XP")
        self.xp_popup.adjustSize()
        parent_width = self.xp_popup.parentWidget().width()
        x = max(8, parent_width - self.xp_popup.width() - 18)
        self.xp_popup.move(x, 8)
        self.xp_popup.show()
        self.xp_popup.raise_()
        self.xp_popup_timer.start(1200)

    def _refresh_progress_label(self) -> None:
        if self.last_progress:
            progress = self.last_progress
            level_span = progress.xp_into_level + progress.xp_to_next_level
            bar_max = max(1, level_span)
            self.progress_changed.emit(
                f"BAR|{progress.level}|{progress.xp_into_level}|{bar_max}|Level {progress.level}: "
                f"{progress.xp_into_level} / {bar_max} XP"
            )
            self.progress_changed.emit(
                f"Adventure XP: +{progress.xp_earned} this run | Total {progress.total_xp} | "
                f"Level {progress.level} | Next level in {progress.xp_to_next_level} XP"
            )
            return

        preview_total = self.total_xp
        preview_level = 1
        preview_next = 100
        if preview_total >= 0:
            preview_level = level_for_total_xp(preview_total)
            preview_next = xp_required_for_level(preview_level + 1) - preview_total
        preview_into_level = xp_required_for_level(preview_level + 1) - preview_next - xp_required_for_level(preview_level)
        preview_span = preview_into_level + preview_next
        self.progress_changed.emit(
            f"BAR|{preview_level}|{preview_into_level}|{max(1, preview_span)}|Level {preview_level}: "
            f"{preview_into_level} / {max(1, preview_span)} XP"
        )

        self.progress_changed.emit(
            f"Adventure XP: +{self.live_session_xp} this run | Total {preview_total} | "
            f"Level {preview_level} | Next level in {preview_next} XP"
        )

    def _apply_progress_bar_style(self, level_up: bool = False) -> None:
        if level_up:
            chunk = "stop:0 #f5d36b, stop:1 #ff9f1c"
            border = "#f5d36b"
        else:
            chunk = "stop:0 #49b7f3, stop:1 #1f78d1"
            border = "#97b8d9"
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid {border};
                border-radius: 6px;
                background: #111827;
                color: #f8fafc;
                text-align: center;
                height: 22px;
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {chunk});
            }}
            """
        )

    def _clear_progress_bar_flash(self) -> None:
        self._apply_progress_bar_style(level_up=False)

    def _animate_progress_bar(self, target_value: int, duration_ms: int = 325) -> None:
        if self._progress_anim:
            self._progress_anim.stop()
        self._progress_anim = QPropertyAnimation(self.progress_bar, b"value", self)
        self._progress_anim.setDuration(duration_ms)
        self._progress_anim.setStartValue(self.progress_bar.value())
        self._progress_anim.setEndValue(target_value)
        self._progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_anim.start()

    def _rollover_progress_bar(self, level: int, value: int, maximum: int, label: str) -> None:
        old_max = max(1, self._progress_bar_maximum)
        current_value = self.progress_bar.value()
        if self._progress_anim:
            self._progress_anim.stop()

        self._progress_anim = QPropertyAnimation(self.progress_bar, b"value", self)
        self._progress_anim.setDuration(220)
        self._progress_anim.setStartValue(current_value)
        self._progress_anim.setEndValue(old_max)
        self._progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _start_new_level_animation() -> None:
            self.progress_bar.setRange(0, maximum)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat(label)
            self._progress_level = level
            self._progress_bar_maximum = maximum
            self._apply_progress_bar_style(level_up=True)
            self._progress_flash_timer.start(850)
            self._animate_progress_bar(value, duration_ms=420)

        self._progress_anim.finished.connect(_start_new_level_animation)
        self._progress_anim.start()

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
            self.playback_position_sec = ev.time
            msg = ev.message.copy()
            is_learning_part = (self.learning_channel is None or msg.channel == self.learning_channel) and (
                self.learning_track is None or ev.track_index == self.learning_track
            )
            if tutor_on and is_learning_part and msg.type == "note_on" and chord_idx < len(chords):
                target_time = start_wall + (ev.time - loop_start) / tempo_mult
                while not self.stop_flag.is_set() and time.perf_counter() < target_time:
                    time.sleep(0.001)
                expected = chords[chord_idx]
                chord_idx += 1
                self.current_expected = expected.notes
                self.playback_position_sec = expected.time
                self.next_cue_time_sec = expected.time
                self.next_cue_notes = set()
                self.waiting_for_input = True
                self.status_changed.emit(f"Next: {sorted(expected.notes)}")
                self.expected_changed.emit(expected.time, expected.notes)
                pause_started = time.perf_counter()
                matched = self.engine.wait_for_notes(expected.notes, timeout=10, strict=self.tutor.strict)
                start_wall = shift_start_for_pause(start_wall, pause_started, time.perf_counter())
                status = "matched" if matched else "timeout"
                self.status_changed.emit(f"Tutor: expected {expected.notes} -> {status}")
                if matched:
                    self._award_live_xp(len(expected.notes))
                self.waiting_for_input = False
                self.next_cue_time_sec = chords[chord_idx].time if chord_idx < len(chords) else None
                self.next_cue_notes = set(chords[chord_idx].notes) if chord_idx < len(chords) else set()
                self.current_expected = set()
                self.expected_changed.emit(expected.time, set())
                continue
            if not track_is_playable(ev.track_index, self.playback.muted_tracks, self.playback.solo_tracks):
                continue
            target_time = start_wall + (ev.time - loop_start) / tempo_mult
            while not self.stop_flag.is_set() and time.perf_counter() < target_time:
                time.sleep(0.001)
            if msg.type in {"note_on", "note_off"} and transpose:
                msg.note = _clamp_note(msg.note + transpose)
            self.engine.send(msg)
        self.engine.all_notes_off()
        self.playback_position_sec = loop_end if loop_end is not None else self.total_time
        self.next_cue_time_sec = None
        self.next_cue_notes = set()
        self.waiting_for_input = False
        self.playback_active = False
        self.status_changed.emit("Playback finished.")
        if chords:
            results = score_performance(chords, self.performance.events)
            counts = Counter(r.verdict for r in results)
            total = len(results)
            summary = f"Score: Perfect={counts.get('PERFECT',0)} Good={counts.get('GOOD',0)} Miss={counts.get('MISS',0)} / {total}"
            progress = calculate_session_progress(results, starting_xp=self.run_start_total_xp)
            self.total_xp = progress.total_xp
            self.last_score_results = results
            self.last_score_summary = summary
            self.last_progress = progress
            self.score_changed.emit(summary)

    def _update_playback_meter(self) -> None:
        current_time = self.playback_position_sec
        total_time = self.total_time
        self.playback_meter_label.setText(
            _playback_meter_text(current_time, total_time, self.next_cue_time_sec, self.waiting_for_input)
        )
        if total_time > 0:
            ratio = max(0.0, min(1.0, current_time / total_time))
            self.song_progress_bar.setValue(int(ratio * 1000))
        else:
            self.song_progress_bar.setValue(0)
        self.roll.set_playhead(current_time)
        self.notation.set_playhead(current_time)

        preview_notes: set[int] = set()
        preview_strength = 0.0
        if self.next_cue_notes and self.next_cue_time_sec is not None and not self.waiting_for_input:
            delta = max(0.0, self.next_cue_time_sec - current_time)
            preview_window = 2.5
            if delta <= preview_window:
                preview_notes = set(self.next_cue_notes)
                preview_strength = 1.0 - min(1.0, delta / preview_window)
        self.keyboard.set_upcoming(preview_notes, preview_strength)

        if not self.playback_active and not self.waiting_for_input:
            self.playback_meter_timer.stop()

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
        self.keyboard.set_expected(notes)
        self.roll.highlight_expected(notes, time_sec)
        self.notation.highlight_expected(notes)

    def on_score_changed(self, text: str) -> None:
        self.score_label.setText(text)
        self._refresh_progress_label()

    def on_progress_changed(self, text: str) -> None:
        if text.startswith("BAR|"):
            _, level, value, maximum, label = text.split("|", 4)
            level_int = int(level)
            value_int = min(int(value), int(maximum))
            maximum_int = max(1, int(maximum))
            if level_int > self._progress_level:
                self._rollover_progress_bar(level_int, value_int, maximum_int, label)
                return
            self.progress_bar.setRange(0, maximum_int)
            self.progress_bar.setFormat(label)
            self._progress_level = level_int
            self._progress_bar_maximum = maximum_int
            self._animate_progress_bar(value_int)
            return
        self.progress_label.setText(text)

    def _restore_ui_preferences(self) -> None:
        prefs = self.settings.get_ui_preferences()
        visible_sections = prefs.get("visible_sections", {})
        for key, toggle in self.view_toggles.items():
            if key in visible_sections:
                toggle.blockSignals(True)
                toggle.setChecked(bool(visible_sections[key]))
                toggle.blockSignals(False)
                self._set_section_visible(key, bool(visible_sections[key]))
        song_sections = prefs.get("song_sections", {})
        for key, section in getattr(self, "song_sections", {}).items():
            if key in song_sections:
                section.set_expanded(bool(song_sections[key]))

    def _save_ui_preferences(self) -> None:
        self.settings.set_ui_preferences(
            {
                "visible_sections": {key: toggle.isChecked() for key, toggle in self.view_toggles.items()},
                "song_sections": {key: section.is_expanded() for key, section in getattr(self, "song_sections", {}).items()},
            }
        )


def run() -> None:
    logger.info("Starting CVP Tutor UI")
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":  # pragma: no cover
    run()
