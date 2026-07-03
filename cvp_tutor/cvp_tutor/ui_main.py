from __future__ import annotations

import json
import os
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
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import QAction, QActionGroup, QColor, QFont, QKeySequence
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
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
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
from .falling_notes import FallingNotesView
from .scoring import score_performance
from .score_view import ScoreView
from .feedback_panel import FeedbackPanel
from .diagnosis import diagnose_performance
from .gamification import GamificationManager


class LevelUpOverlay(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #FFD700; font-weight: bold; text-shadow: 0px 0px 10px rgba(0,0,0,0.8);")
        
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        
        self.anim = QPropertyAnimation(self.effect, b"opacity")
        self.anim.setDuration(3000)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def show_level(self, level: int):
        self.label.setText(f"LEVEL UP!\nRANK {level}")
        # Scale font relative to window height
        h = self.parent().height()
        font_size = int(h / 10)
        self.label.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        
        self.resize(self.parent().size())
        self.label.resize(self.size())
        self.raise_()
        self.show()
        
        self.anim.setStartValue(0.0)
        self.anim.setKeyValueAt(0.1, 1.0) # Fade in quick
        self.anim.setKeyValueAt(0.8, 1.0) # Hold
        self.anim.setEndValue(0.0)        # Fade out
        self.anim.start()
        
    def resizeEvent(self, event):
        self.label.resize(self.size())
        super().resizeEvent(event)


# Predefined color themes (background, foreground, accent, panel)
THEMES = {
    "Default": {"bg": "#f7f7f7", "fg": "#111111", "accent": "#3b82f6", "panel": "#ffffff"},
    "Pretty": {"bg": "#f4f6ff", "fg": "#0b1020", "accent": "#8b5cf6", "panel": "#ffffff"},
    "Irish": {"bg": "#e8f8ec", "fg": "#083b11", "accent": "#2e7d32", "panel": "#f7fff8"},
    "Halloween": {"bg": "#1b1b1b", "fg": "#f3b236", "accent": "#ff6f00", "panel": "#2b2b2b"},
    "Christmas": {"bg": "#fff6f6", "fg": "#1b2a1f", "accent": "#b71c1c", "panel": "#f7fff7"},
    "Aussie": {"bg": "#eaf6ff", "fg": "#05314a", "accent": "#00a86b", "panel": "#ffffff"},
}


def _clamp_note(value: int) -> int:
    return max(0, min(127, value))


class MainWindow(QMainWindow):
    status_changed = pyqtSignal(str)
    expected_changed = pyqtSignal(float, object)  # time_sec, notes set
    score_changed = pyqtSignal(str)
    hero_changed = pyqtSignal(str)
    reward_awarded = pyqtSignal(int, int)  # xp, gold
    achievement_unlocked = pyqtSignal(str, str)
    midi_signal = pyqtSignal(object)  # marshal MIDI events to UI thread
    next_expected_changed = pyqtSignal(object)  # set of notes to highlight in UI
    hint_enabled_changed = pyqtSignal(bool)
    feedback_event = pyqtSignal(object)
    feedback_bar = pyqtSignal(int, int)
    diagnosis_changed = pyqtSignal(str, bool)  # html text, visible
    playback_time_changed = pyqtSignal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CVP Tutor")
        self.resize(1280, 780)
        self.engine = MidiIO()
        self.playback = PlaybackEngine(self.engine)
        self.tutor = TutorEngine()
        self.performance = PerformanceCapture(self.engine)
        self.gamification = GamificationManager(Path("data") / "hero_profile.json")
        self.engine.register_listener(lambda msg: self.midi_signal.emit(msg))
        self.midi_file: Optional[Path] = None
        self.parts: List[MidiPart] = []
        self.events: List[MidiEvent] = []
        self.total_time: float = 0.0
        self.learning_tracks: set[int] | None = None
        self.sections: dict[str, QWidget] = {}
        self.play_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self.loop_start = 0.0
        self.loop_end: Optional[float] = None
        self.learning_channel: Optional[int] = None
        self.current_expected: set[int] = set()
        self._gamified_during_playback = False

        self.current_level, _, _ = self.gamification.get_progress()
        self.level_overlay = LevelUpOverlay(self)

        self._playback_time_lock = threading.Lock()
        self._playback_time_sec = 0.0
        self._last_position_emit = 0.0
        self.settings = QSettings("ParrisPiano", "CVP Tutor")

        self._build_menu()
        self._build_ui()
        self._apply_saved_note_display_mode()
        self.expected_changed.connect(self.on_expected_changed)
        self.score_changed.connect(self.on_score_changed)
        self.hero_changed.connect(self._update_hero)
        self.reward_awarded.connect(self._on_reward_awarded)
        self.achievement_unlocked.connect(self._on_achievement_unlocked)
        self.midi_signal.connect(self.on_midi_in)
        self.next_expected_changed.connect(self._set_next_expected)
        self.hint_enabled_changed.connect(self.hint_btn.setEnabled)
        self.feedback_event.connect(self.feedback.add_score_event)
        self.feedback_bar.connect(self.feedback.update_bar_score)
        self.diagnosis_changed.connect(self._set_diagnosis)
        self.status_changed.connect(self._update_status)
        self.playback_time_changed.connect(self._on_playback_position)
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
        self.learning_list = QListWidget()
        self.learning_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.learning_list.setMinimumHeight(70)
        self.learning_list.itemChanged.connect(self._learning_selection_changed)
        self.select_all_btn = QPushButton("All")
        self.select_all_btn.setFixedWidth(48)
        self.select_all_btn.clicked.connect(lambda: self._set_learning_checks(all_parts=True))
        self.select_melodic_btn = QPushButton("Melodic")
        self.select_melodic_btn.setFixedWidth(68)
        self.select_melodic_btn.clicked.connect(lambda: self._set_learning_checks(all_parts=False))
        self.select_melody_btn = QPushButton("Melody")
        self.select_melody_btn.setFixedWidth(68)
        self.select_melody_btn.clicked.connect(self._select_melody_track)
        self.select_none_btn = QPushButton("None")
        self.select_none_btn.setFixedWidth(48)
        self.select_none_btn.clicked.connect(self._clear_learning_checks)
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
        self.save_take_btn = QPushButton("Save Take as MIDI")
        self.save_take_btn.clicked.connect(self.save_take)

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
        self.transpose_slider.setToolTip(
            "Shifts playback and on-screen notes together so the keyboard, tutor, and note views stay aligned."
        )

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
        self.hint_btn = QPushButton("Hint (Play Expected Chord)")
        self.hint_btn.clicked.connect(self.play_hint)
        self.hint_btn.setEnabled(False)

        self.position_label = QLabel("Playhead: -- / --")
        self.loop_len_spin = QDoubleSpinBox()
        self.loop_len_spin.setRange(0.25, 600.0)
        self.loop_len_spin.setValue(2.0)
        self.loop_len_spin.setDecimals(2)
        self.loop_len_spin.setSuffix(" s")
        self.loop_from_playhead_btn = QPushButton("Set loop from playhead")
        self.loop_from_playhead_btn.setToolTip(
            "Sets loop start to the current playhead and end to playhead + loop length (for bar or phrase practice)."
        )
        self.loop_from_playhead_btn.clicked.connect(self.set_loop_from_playhead)
        self.clear_loop_btn = QPushButton("Clear loop")
        self.clear_loop_btn.setToolTip("Full song: loop from 0s to end.")
        self.clear_loop_btn.clicked.connect(self.clear_loop_region)
        self.repeat_loop_chk = QCheckBox("Repeat loop region")
        self.repeat_loop_chk.setToolTip(
            "When loop start and end are set, jump back to the start after the end for repeated practice."
        )

        f_layout.addWidget(open_btn, 0, 0)
        f_layout.addWidget(self.file_label, 0, 1, 1, 3)

        f_layout.addWidget(self.sheet_btn, 1, 0)
        f_layout.addWidget(self.export_btn, 1, 1)
        parts_label = QHBoxLayout()
        parts_label.addWidget(QLabel("Learning Parts"))
        parts_label.addStretch()
        parts_label.addWidget(self.select_all_btn)
        parts_label.addWidget(self.select_melodic_btn)
        parts_label.addWidget(self.select_melody_btn)
        parts_label.addWidget(self.select_none_btn)
        f_layout.addLayout(parts_label, 1, 2)
        f_layout.addWidget(self.learning_list, 1, 3)

        f_layout.addWidget(self.play_btn, 2, 0)
        f_layout.addWidget(self.stop_btn, 2, 1)
        f_layout.addWidget(self.save_take_btn, 2, 2)
        f_layout.addWidget(self.tutor_toggle, 2, 3)

        f_layout.addWidget(self.hint_btn, 3, 0, 1, 4)

        f_layout.addWidget(self.tempo_label, 4, 0)
        f_layout.addWidget(self.tempo_slider, 4, 1, 1, 3)

        f_layout.addWidget(self.transpose_label, 5, 0)
        f_layout.addWidget(self.transpose_slider, 5, 1, 1, 3)

        f_layout.addWidget(loop_label, 6, 0)
        f_layout.addWidget(self.loop_start_spin, 6, 1)
        f_layout.addWidget(self.loop_end_spin, 6, 2)
        f_layout.addWidget(self.repeat_loop_chk, 6, 3)

        f_layout.addWidget(self.position_label, 7, 0, 1, 2)
        loop_len_lbl = QLabel("Loop length")
        f_layout.addWidget(loop_len_lbl, 7, 2)
        f_layout.addWidget(self.loop_len_spin, 7, 3)
        f_layout.addWidget(self.loop_from_playhead_btn, 8, 0, 1, 2)
        f_layout.addWidget(self.clear_loop_btn, 8, 2, 1, 2)
        f_layout.setColumnStretch(1, 1)
        f_layout.setColumnStretch(2, 1)
        f_layout.setColumnStretch(3, 1)
        file_box.setLayout(f_layout)

        # Feedback panel
        self.feedback = FeedbackPanel()
        self.sections["feedback"] = self.feedback
        layout.addWidget(self.feedback)

        tabs = QTabWidget()
        self.tabs = tabs
        self.keyboard = KeyboardView()
        self.keyboard.setStyleSheet("background: #f7f7f7; border: 1px solid #d0d0d0;")
        self.roll = PianoRollView()
        self.falling = FallingNotesView()
        self.note_display_stack = QStackedWidget()
        self.note_display_stack.addWidget(self.roll)
        self.note_display_stack.addWidget(self.falling)
        self.score = ScoreView()
        tabs.addTab(self.keyboard, "Keyboard")
        tabs.addTab(self.note_display_stack, "Notes")
        tabs.addTab(self.score, "Score")
        self.sections["views"] = tabs
        layout.addWidget(tabs)

        # Status and diagnosis
        self.status = QLabel("Ready")
        self.score_label = QLabel("Score: --")
        self.diagnosis_label = QLabel("")
        self.diagnosis_label.setWordWrap(True)
        self.diagnosis_label.setStyleSheet("background: #fff3cd; border: 1px solid #ffc107; padding: 8px; border-radius: 4px;")
        self.diagnosis_label.setMinimumHeight(60)
        self.diagnosis_label.hide()  # Hide until diagnosis is available
        status_box = QGroupBox("Status")
        s_layout = QVBoxLayout()
        s_layout.setContentsMargins(8, 6, 8, 6)
        s_layout.setSpacing(6)
        s_layout.addWidget(self.status)
        s_layout.addWidget(self.score_label)
        s_layout.addWidget(self.diagnosis_label)
        # Hero / gamification status
        hero_box = QWidget()
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        self.hero_level_label = QLabel(f"Lv {self.current_level}")
        self.hero_level_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        self.hero_xp_bar = QProgressBar()
        self.hero_xp_bar.setTextVisible(True)
        # Stylesheet handled by apply_theme
        
        self.hero_gold_label = QLabel(f"Gold: {self.gamification.profile.gold}")
        
        h_layout.addWidget(self.hero_level_label)
        h_layout.addWidget(self.hero_xp_bar)
        h_layout.addWidget(self.hero_gold_label)
        hero_box.setLayout(h_layout)
        s_layout.addWidget(hero_box)
        
        # Initialize bar
        lvl, xp, mx = self.gamification.get_progress()
        self.hero_xp_bar.setMaximum(mx)
        self.hero_xp_bar.setValue(xp)
        self.hero_xp_bar.setFormat(f"XP {xp}/{mx}")

        # Transient reward label (cleared after a few seconds)
        self.reward_label = QLabel("")
        self.reward_label.setStyleSheet("color: #16a34a; font-weight: bold;")
        s_layout.addWidget(self.reward_label)
        status_box.setLayout(s_layout)
        self.sections["status"] = status_box

        # View toggles
        view_box = QGroupBox("View / Layout")
        v_layout = QGridLayout()
        v_layout.setHorizontalSpacing(8)
        v_layout.setVerticalSpacing(4)
        self.toggle_feedback = QCheckBox("Show Feedback")
        self.toggle_feedback.setChecked(True)
        self.toggle_feedback.toggled.connect(lambda v: self._toggle_section("feedback", v))
        self.toggle_views = QCheckBox("Show Keyboard / Notes / Score")
        self.toggle_views.setChecked(True)
        self.toggle_views.toggled.connect(lambda v: self._toggle_section("views", v))
        self.toggle_devices = QCheckBox("Show MIDI Devices")
        self.toggle_devices.setChecked(True)
        self.toggle_devices.toggled.connect(lambda v: self._toggle_section("devices", v))
        self.toggle_song = QCheckBox("Show Song Controls")
        self.toggle_song.setChecked(True)
        self.toggle_song.toggled.connect(lambda v: self._toggle_section("song", v))
        self.toggle_status = QCheckBox("Show Status/Score")
        self.toggle_status.setChecked(True)
        self.toggle_status.toggled.connect(lambda v: self._toggle_section("status", v))
        v_layout.addWidget(self.toggle_feedback, 0, 0)
        v_layout.addWidget(self.toggle_views, 0, 1)
        v_layout.addWidget(self.toggle_devices, 1, 0)
        v_layout.addWidget(self.toggle_song, 1, 1)
        v_layout.addWidget(self.toggle_status, 2, 0)
        v_layout.addWidget(QLabel("Note display"), 3, 0)
        self.note_display_combo = QComboBox()
        self.note_display_combo.addItem("Horizontal roll + playhead", "horizontal")
        self.note_display_combo.addItem("Falling notes (lanes)", "falling")
        self.note_display_combo.setToolTip(
            "Choose one visualization. Both follow playback in real time; preference is saved."
        )
        self.note_display_combo.currentIndexChanged.connect(self._on_note_display_combo_changed)
        v_layout.addWidget(self.note_display_combo, 3, 1, 1, 1)
        view_box.setLayout(v_layout)

        self.sections["devices"] = devices_box
        self.sections["song"] = file_box

        layout.addWidget(view_box)
        layout.addWidget(devices_box)
        layout.addWidget(file_box)
        layout.addWidget(status_box)
        root.setLayout(layout)
        self.setCentralWidget(root)
        # Apply default theme
        self.apply_theme("Default")

    def _build_menu(self) -> None:
        """Create a simple menu bar with File and View->Theme entries."""
        try:
            menubar = self.menuBar()

            # File menu
            file_menu = menubar.addMenu("File")
            open_action = QAction("Open MIDI", self)
            open_action.triggered.connect(self.open_file)
            file_menu.addAction(open_action)
            exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

            # View / Theme menu
            view_menu = menubar.addMenu("View")
            theme_menu = view_menu.addMenu("Theme")
            ag = QActionGroup(self)
            for t in THEMES.keys():
                a = QAction(t, self)
                a.setCheckable(True)
                a.triggered.connect(lambda checked, name=t: self.apply_theme(name))
                theme_menu.addAction(a)
                ag.addAction(a)
            # Hero / Achievements
            hero_menu = menubar.addMenu("Hero")
            ach_action = QAction("Achievements", self)
            ach_action.triggered.connect(self.show_achievements)
            hero_menu.addAction(ach_action)

            settings_menu = menubar.addMenu("Settings")
            nd_menu = settings_menu.addMenu("Note display")
            self._note_display_group = QActionGroup(self)
            self._act_note_horizontal = QAction("Horizontal roll + playhead", self)
            self._act_note_horizontal.setCheckable(True)
            self._act_note_falling = QAction("Falling notes (lanes)", self)
            self._act_note_falling.setCheckable(True)
            self._note_display_group.addAction(self._act_note_horizontal)
            self._note_display_group.addAction(self._act_note_falling)
            self._act_note_horizontal.triggered.connect(lambda: self._set_note_display_mode("horizontal", persist=True))
            self._act_note_falling.triggered.connect(lambda: self._set_note_display_mode("falling", persist=True))
            nd_menu.addAction(self._act_note_horizontal)
            nd_menu.addAction(self._act_note_falling)

            help_menu = menubar.addMenu("Help")
            logs_action = QAction("Open logs folder", self)
            logs_action.triggered.connect(self.open_logs_folder)
            help_menu.addAction(logs_action)
        except Exception:
            # If menu creation fails for any PyQt build, ignore and continue
            pass

    def apply_theme(self, name: str) -> None:
        """Apply a named theme by setting a simple stylesheet."""
        theme = THEMES.get(name, THEMES["Default"])
        bg = theme["bg"]
        fg = theme["fg"]
        accent = theme["accent"]
        panel = theme["panel"]

        # Basic stylesheet that affects main widgets
        sheet = f"""
        QWidget {{ background: {bg}; color: {fg}; }}
        QGroupBox {{ background: {panel}; border: 1px solid {accent}; border-radius: 6px; margin-top: 6px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 3px 0 3px; color: {fg}; }}
        QPushButton {{ background: {accent}; color: white; border: none; padding: 6px 10px; border-radius: 4px; }}
        QPushButton:disabled {{ background: #888888; }}
        QComboBox {{ background: {panel}; padding: 4px; border: 1px solid {accent}; border-radius: 4px; color: {fg}; }}
        QComboBox::item {{ background: {panel}; color: {fg}; }}
        QLabel {{ color: {fg}; }}
        QTabWidget::pane {{ background: {panel}; border: 1px solid {accent}; }}
        QTabBar::tab {{ background: {panel}; color: {fg}; border: 1px solid {accent}; padding: 5px; margin-right: 2px; }}
        QTabBar::tab:selected {{ background: {accent}; color: white; }}
        QSlider::groove:horizontal {{ height: 6px; background: {panel}; border: 1px solid {accent}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {accent}; width: 12px; margin: -4px 0; border-radius: 6px; }}
        QCheckBox {{ color: {fg}; }}
        QScrollArea {{ background: {panel}; }}
        QListWidget {{ background: {panel}; color: {fg}; border: 1px solid {accent}; }}
        QProgressBar {{ border: 1px solid {accent}; border-radius: 4px; text-align: center; background: {panel}; color: {fg}; font-weight: bold; min-height: 20px; }}
        QProgressBar::chunk {{ background-color: {accent}; border-radius: 3px; }}
        """

        app = QApplication.instance()
        if app:
            app.setStyleSheet(sheet)
        
        # Propagate to custom views
        try:
            self.keyboard.set_colors(theme)
            self.roll.set_colors(theme)
            self.falling.set_colors(theme)
        except Exception:
            pass

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
        self.learning_tracks = None
        self.learning_channel = None
        self.render_score_pdf()
        self.file_label.setText(f"{path.name} ({self.total_time:.1f}s)")
        with self._playback_time_lock:
            self._playback_time_sec = 0.0
        self.position_label.setText(f"Playhead: 0.00s / {self.total_time:.2f}s")
        self.learning_list.blockSignals(True)
        self.learning_list.clear()
        for idx, part in enumerate(self.parts):
            ch = f"ch {part.channel}" if part.channel is not None else "ch ?"
            item = QListWidgetItem(f"{idx}: {part.name} ({ch}) notes={part.note_count}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            default_check = Qt.CheckState.Unchecked
            if part.channel != 9:  # skip percussion by default
                default_check = Qt.CheckState.Checked
            item.setCheckState(default_check)
            item.setData(Qt.ItemDataRole.UserRole, part)
            self.learning_list.addItem(item)
        self.learning_list.blockSignals(False)
        self._learning_selection_changed()

    def _learning_selection_changed(self) -> None:
        selected_parts: List[MidiPart] = []
        for i in range(self.learning_list.count()):
            item = self.learning_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                part = item.data(Qt.ItemDataRole.UserRole)
                if part:
                    selected_parts.append(part)
        if not selected_parts:
            # If nothing selected, fall back to all parts so tutor still waits
            self.learning_tracks = None
            self.learning_channel = None
        else:
            self.learning_tracks = {p.track_index for p in selected_parts}
            channels = {p.channel for p in selected_parts if p.channel is not None}
            self.learning_channel = channels.pop() if len(channels) == 1 else None
        self.current_expected = set()
        self.keyboard.set_expected(set())
        if self.midi_file:
            tr = self.transpose_slider.value()
            count = self.roll.load_notes(
                self.events,
                self.learning_channel,
                None,
                self.total_time,
                show_all=True,
                learning_tracks=self.learning_tracks if self.learning_tracks else None,
                transpose_semitones=tr,
            )
            self.falling.load_notes(
                self.events,
                self.learning_channel,
                None,
                self.total_time,
                show_all=True,
                learning_tracks=self.learning_tracks if self.learning_tracks else None,
                transpose_semitones=tr,
            )
            self.status.setText(f"Piano Roll notes: {count}")

    def _toggle_section(self, key: str, visible: bool) -> None:
        widget = self.sections.get(key)
        if widget:
            widget.setVisible(visible)

    def _set_learning_checks(self, all_parts: bool) -> None:
        """Quick-select learning parts. If all_parts is False, select melodic (non-drum) only."""
        self.learning_list.blockSignals(True)
        for i in range(self.learning_list.count()):
            item = self.learning_list.item(i)
            part: MidiPart = item.data(Qt.ItemDataRole.UserRole)
            if not part:
                continue
            is_drum = (part.channel == 9)
            if all_parts:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked if is_drum else Qt.CheckState.Checked)
        self.learning_list.blockSignals(False)
        self._learning_selection_changed()

    def _clear_learning_checks(self) -> None:
        """Uncheck all learning part checkboxes."""
        self.learning_list.blockSignals(True)
        for i in range(self.learning_list.count()):
            item = self.learning_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self.learning_list.blockSignals(False)
        self._learning_selection_changed()

    def _select_melody_track(self) -> None:
        """Detect the melody track and select only that part in the learning list."""
        melody_idx = self._detect_melody_track()
        if melody_idx is None:
            self.status.setText("Melody not detected.")
            return
        # Uncheck all, then check only the matching part(s)
        self.learning_list.blockSignals(True)
        found = False
        for i in range(self.learning_list.count()):
            item = self.learning_list.item(i)
            part: MidiPart = item.data(Qt.ItemDataRole.UserRole)
            if not part:
                continue
            if part.track_index == melody_idx:
                item.setCheckState(Qt.CheckState.Checked)
                found = True
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.learning_list.blockSignals(False)
        if found:
            self.status.setText(f"Selected melody track: {melody_idx}")
        self._learning_selection_changed()

    def _detect_melody_track(self) -> int | None:
        """Heuristic to find the melody/main vocal line track.

        Scans `self.parts` and `self.events` and scores each part by how
        monophonic and prominent it is. Returns the `track_index` of the
        best candidate or None if no suitable track found.
        """
        if not self.parts or not self.events:
            return None

        # Group events by track_index
        tracks: dict[int, list] = {}
        for ev in self.events:
            tracks.setdefault(ev.track_index, []).append(ev)

        scores: dict[int, float] = {}
        max_note_count = max((len([e for e in evs if e.message.type == 'note_on' and getattr(e.message,'velocity',1)>0]) for evs in tracks.values()), default=1)

        for track_idx, evs in tracks.items():
            # Collect note on/off events for the track
            evs_sorted = sorted(evs, key=lambda e: e.time)
            active: dict[int, float] = {}
            total_note_time = 0.0
            mono_time = 0.0
            note_durations: list[float] = []
            last_time = evs_sorted[0].time if evs_sorted else 0.0

            # We'll track active count between event times
            for ev in evs_sorted:
                cur_time = ev.time
                delta = cur_time - last_time
                active_count = len(active)
                if active_count > 0:
                    total_note_time += delta
                    if active_count <= 1:
                        mono_time += delta
                # process event
                msg = ev.message
                if msg.type == 'note_on' and getattr(msg, 'velocity', 1) > 0:
                    # start note
                    active[msg.note] = cur_time
                elif msg.type == 'note_off' or (msg.type == 'note_on' and getattr(msg, 'velocity', 0) == 0):
                    start = active.pop(msg.note, None)
                    if start is not None:
                        dur = cur_time - start
                        if dur > 0:
                            note_durations.append(dur)
                last_time = cur_time

            # after loop, we won't account trailing active notes
            note_count = sum(1 for e in evs if e.message.type == 'note_on' and getattr(e.message,'velocity',1)>0)
            avg_dur = (sum(note_durations) / len(note_durations)) if note_durations else 0.0
            mono_fraction = (mono_time / total_note_time) if total_note_time > 0 else 0.0

            # Normalize note_count and avg_dur modestly
            norm_count = note_count / max_note_count if max_note_count > 0 else 0.0
            norm_dur = min(avg_dur / 1.0, 1.0)  # prefer average durations up to ~1s

            # Score: prioritize monophonic lines, then note density and sustain
            score = mono_fraction * 0.6 + norm_count * 0.25 + norm_dur * 0.15
            scores[track_idx] = score

        if not scores:
            return None
        # pick best track index
        best = max(scores.items(), key=lambda kv: kv[1])
        return best[0]

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

    def save_take(self) -> None:
        """Save the captured performance to a MIDI file."""
        if not self.performance.events:
            self.status.setText("No captured take yet. Play once before saving.")
            return
        default_name = "performance_take.mid"
        if self.midi_file:
            default_name = self.midi_file.with_suffix(".take.mid").name
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Take", default_name, "MIDI Files (*.mid *.midi)")
        if not save_path:
            return
        try:
            self.performance.export_midi(Path(save_path))
            self.status.setText(f"Saved take: {Path(save_path).name}")
        except Exception as exc:
            self.status.setText(f"Save failed: {exc}")

    def _update_hero(self, text: str) -> None:
        try:
            level, xp, max_xp = self.gamification.get_progress()
            self.hero_level_label.setText(f"Lv {level}")
            self.hero_xp_bar.setMaximum(max_xp)
            self.hero_xp_bar.setValue(xp)
            self.hero_xp_bar.setFormat(f"XP {xp}/{max_xp}")
            self.hero_gold_label.setText(f"Gold: {self.gamification.profile.gold}")
            
            if level > self.current_level:
                self.current_level = level
                self.level_overlay.show_level(level)
        except Exception:
            pass

    def _on_reward_awarded(self, xp: int, gold: int) -> None:
        try:
            text = f"+{xp} XP  +{gold} Gold"
            self.reward_label.setText(text)
            QTimer.singleShot(3000, lambda: self.reward_label.setText(""))
        except Exception:
            pass

    def _on_achievement_unlocked(self, name: str, description: str) -> None:
        try:
            # transient achievement display; use message box for prominence
            QMessageBox.information(self, "Achievement Unlocked!", f"{name}\n\n{description}")
        except Exception:
            pass

    def show_achievements(self) -> None:
        try:
            # Try to collect achievements from dnd manager if present
            ach_list = []
            try:
                if getattr(self.gamification, "dnd", None):
                    for a in self.gamification.dnd.profile.achievements:
                        ach_list.append(f"{a.name}: {a.description} (unlocked: {a.unlocked_at})")
            except Exception:
                pass
            # fallback: read achievements.json
            if not ach_list:
                ach_file = Path("data") / "achievements.json"
                if ach_file.exists():
                    try:
                        raw = json.loads(ach_file.read_text())
                        for a in raw:
                            ach_list.append(f"{a.get('name')}: {a.get('description')} (unlocked: {a.get('unlocked_at')})")
                    except Exception:
                        pass

            if not ach_list:
                QMessageBox.information(self, "Achievements", "No achievements unlocked yet.")
                return

            text = "\n\n".join(ach_list)
            QMessageBox.information(self, "Achievements", text)
        except Exception:
            pass

    def _tempo_changed(self, value: int) -> None:
        self.tempo_label.setText(f"Tempo {value/100:.2f}x")

    def _transpose_changed(self, value: int) -> None:
        self.transpose_label.setText(f"Transpose {value:+d}")
        self._reload_note_views()

    def _reload_note_views(self) -> None:
        """Keep roll / falling in sync with Transpose slider (same as tutor + keyboard)."""
        if not self.events:
            return
        tr = self.transpose_slider.value()
        self.roll.load_notes(
            self.events,
            self.learning_channel,
            None,
            self.total_time,
            show_all=True,
            learning_tracks=self.learning_tracks if self.learning_tracks else None,
            transpose_semitones=tr,
        )
        self.falling.load_notes(
            self.events,
            self.learning_channel,
            None,
            self.total_time,
            show_all=True,
            learning_tracks=self.learning_tracks if self.learning_tracks else None,
            transpose_semitones=tr,
        )

    @staticmethod
    def _first_chord_index_at_or_after(chords, loop_start: float) -> int:
        for i, c in enumerate(chords):
            if c.time >= loop_start - 1e-6:
                return i
        return len(chords)

    @staticmethod
    def _count_chords_before(chords, loop_start: float) -> int:
        return sum(1 for c in chords if c.time < loop_start - 1e-6)

    def _emit_playhead(self, t: float) -> None:
        with self._playback_time_lock:
            self._playback_time_sec = t
        now = time.perf_counter()
        if now - self._last_position_emit >= 0.04:
            self._last_position_emit = now
            self.playback_time_changed.emit(t)

    def _on_playback_position(self, t: float) -> None:
        tot = self.total_time or 0.0
        self.position_label.setText(f"Playhead: {t:.2f}s / {tot:.2f}s")
        try:
            self.roll.set_playback_time(t)
            self.falling.set_playback_time(t)
        except Exception:
            pass

    def _apply_saved_note_display_mode(self) -> None:
        mode = self.settings.value("note_display_mode", "horizontal")
        if mode not in ("horizontal", "falling"):
            mode = "horizontal"
        self._set_note_display_mode(mode, persist=False)

    def _set_note_display_mode(self, mode: str, persist: bool = True) -> None:
        if mode not in ("horizontal", "falling"):
            mode = "horizontal"
        if persist:
            self.settings.setValue("note_display_mode", mode)
        if mode == "horizontal":
            self.note_display_stack.setCurrentWidget(self.roll)
            if getattr(self, "_act_note_horizontal", None):
                self._act_note_horizontal.setChecked(True)
        else:
            self.note_display_stack.setCurrentWidget(self.falling)
            if getattr(self, "_act_note_falling", None):
                self._act_note_falling.setChecked(True)
        if hasattr(self, "note_display_combo"):
            self.note_display_combo.blockSignals(True)
            self.note_display_combo.setCurrentIndex(0 if mode == "horizontal" else 1)
            self.note_display_combo.blockSignals(False)
        with self._playback_time_lock:
            pt = self._playback_time_sec
        self.roll.set_playback_time(pt)
        self.falling.set_playback_time(pt)

    def _on_note_display_combo_changed(self) -> None:
        mode = self.note_display_combo.currentData()
        if isinstance(mode, str) and mode in ("horizontal", "falling"):
            self._set_note_display_mode(mode, persist=True)

    def set_loop_from_playhead(self) -> None:
        if not self.events:
            self.status.setText("Load a MIDI file first.")
            return
        pos = self._playback_time_sec
        length = self.loop_len_spin.value()
        start = max(0.0, pos)
        end = start + length
        if self.total_time > 0:
            end = min(end, self.total_time)
        if end < start + 0.05:
            self.status.setText("Loop length too small for the remaining song.")
            return
        self.loop_start_spin.setValue(start)
        self.loop_end_spin.setValue(end)
        self.status.setText(f"Loop set: {start:.2f}s – {end:.2f}s")

    def clear_loop_region(self) -> None:
        self.loop_start_spin.setValue(0.0)
        self.loop_end_spin.setValue(0.0)
        self.status.setText("Loop cleared (full song).")

    def open_logs_folder(self) -> None:
        logs = Path("logs").resolve()
        logs.mkdir(exist_ok=True)
        try:
            os.startfile(str(logs))  # type: ignore[attr-defined]
        except OSError:
            self.status.setText("Could not open logs folder.")
    
    def play_hint(self) -> None:
        """Play the expected chord softly as a hint (all notes together)."""
        if not self.current_expected:
            self.status.setText("No expected notes to hint.")
            return

        notes = sorted(self.current_expected)

        def play_hint_notes() -> None:
            vel = 30
            hold = 0.35
            for n in notes:
                self.engine.send(mido.Message("note_on", note=n, velocity=vel, channel=0))
            time.sleep(hold)
            for n in notes:
                self.engine.send(mido.Message("note_off", note=n, velocity=0, channel=0))

        thread = threading.Thread(target=play_hint_notes, daemon=True)
        thread.start()
        self.status.setText(f"Playing hint chord: {notes}")

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
        chords = group_expected(self.events, self.learning_channel, None, self.learning_tracks if self.learning_tracks else None)
        if tutor_on:
            initial_expected = chords[0].notes if chords else set()
            self.expected_changed.emit(chords[0].time if chords else 0.0, initial_expected)
        else:
            self.expected_changed.emit(0.0, set())
        self.stop_flag.clear()
        self._gamified_during_playback = False
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
        session_repeating = (
            self.repeat_loop_chk.isChecked()
            and loop_end is not None
            and loop_end > loop_start + 1e-6
        )

        def finalize_tutor_session() -> None:
            if not chords:
                return
            results = score_performance(chords, self.performance.events)
            counts = Counter(r.verdict for r in results)
            total = len(results)
            perfect = counts.get("PERFECT", 0)
            good = counts.get("GOOD", 0)
            late = counts.get("LATE", 0)
            early = counts.get("EARLY", 0)
            miss = counts.get("MISS", 0)
            wrong = counts.get("WRONG", 0)
            summary = f"Score: Perfect={perfect} Good={good} Late={late} Early={early} Miss={miss} Wrong={wrong} / {total}"
            self.score_changed.emit(summary)
            if not self._gamified_during_playback:
                try:
                    reward = self.gamification.apply_score(results)
                    logger.info(
                        f"Gamification reward: xp={reward.xp_gained} gold={reward.gold_gained} notes={reward.notes} perfect={reward.perfect} good={reward.good}"
                    )
                    self.hero_changed.emit(self.gamification.hero_text(reward))
                    self.reward_awarded.emit(reward.xp_gained, reward.gold_gained)
                except Exception:
                    pass
            insights = diagnose_performance(results, chords)
            if insights:
                insight_text = "\n".join(
                    [f"> {insight.message}\n  -> {insight.drill_suggestion}" for insight in insights]
                )
                html = f"<b>Practice Insights:</b><br>{insight_text.replace(chr(10), '<br>')}"
                self.diagnosis_changed.emit(html, True)
            else:
                self.diagnosis_changed.emit("", False)

        if tutor_on:
            self._emit_playhead(loop_start)
            while not self.stop_flag.is_set():
                chord_idx = self._first_chord_index_at_or_after(chords, loop_start)
                waited_chords: set[float] = set()
                start_wall = time.perf_counter()
                if session_repeating:
                    self.performance.reset()
                hit_loop_boundary = False

                for ev in self.events:
                    if self.stop_flag.is_set():
                        break
                    if ev.time < loop_start:
                        continue
                    if loop_end and ev.time > loop_end:
                        if session_repeating:
                            hit_loop_boundary = True
                        break

                    self._emit_playhead(ev.time)

                    track_ok = True if self.learning_tracks is None else ev.track_index in self.learning_tracks
                    chan_ok = self.learning_channel is None or ev.message.channel == self.learning_channel
                    is_learning_part = track_ok and chan_ok

                    if (
                        is_learning_part
                        and ev.message.type == "note_on"
                        and ev.message.velocity > 0
                        and chord_idx < len(chords)
                    ):
                        expected = chords[chord_idx]
                        chord_time = expected.time

                        if abs(ev.time - chord_time) < 0.05 and chord_time not in waited_chords:
                            target_notes = {_clamp_note(n + transpose) for n in expected.notes}

                            self.current_expected = target_notes
                            self.status_changed.emit(f"Waiting for: {sorted(target_notes)}")
                            self.expected_changed.emit(expected.time, target_notes)
                            self._emit_playhead(expected.time)

                            wait_start = time.perf_counter()
                            while not self.stop_flag.is_set():
                                current_held = set(self.keyboard.held_notes)
                                if target_notes.issubset(current_held):
                                    break
                                time.sleep(0.01)

                            wait_duration = time.perf_counter() - wait_start
                            start_wall += wait_duration

                            self.status_changed.emit(f"Matched: {sorted(target_notes)}")
                            self.current_expected = set()
                            self.expected_changed.emit(ev.time, set())
                            waited_chords.add(chord_time)
                            try:
                                from .timeline import ExpectedMoment

                                expected_moments = [
                                    ExpectedMoment(
                                        time=expected.time,
                                        notes=expected.notes,
                                        track_index=expected.track_index,
                                        channel=expected.channel,
                                    )
                                ]
                                immediate_results = score_performance(expected_moments, self.performance.events)
                                for r in immediate_results:
                                    self.feedback_event.emit(r)
                                    try:
                                        reward = self.gamification.apply_score([r])
                                        logger.info(
                                            f"Gamification (immediate): xp={reward.xp_gained} gold={reward.gold_gained} verdict={r.verdict}"
                                        )
                                        self.hero_changed.emit(self.gamification.hero_text(reward))
                                        self.reward_awarded.emit(reward.xp_gained, reward.gold_gained)
                                        try:
                                            unlocked = self.gamification.check_achievements()
                                            for a in unlocked:
                                                self.achievement_unlocked.emit(
                                                    a.get("name", "Achievement"), a.get("description", "")
                                                )
                                        except Exception:
                                            pass
                                        self._gamified_during_playback = True
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            chord_idx += 1

                        continue

                    target_time = start_wall + (ev.time - loop_start) / tempo_mult
                    while not self.stop_flag.is_set() and time.perf_counter() < target_time:
                        time.sleep(0.001)

                    msg = ev.message.copy()
                    if msg.type in {"note_on", "note_off"} and transpose:
                        msg.note = _clamp_note(msg.note + transpose)

                    if not (is_learning_part and msg.type == "note_on" and msg.velocity > 0):
                        self.engine.send(msg)

                if self.stop_flag.is_set():
                    break
                if hit_loop_boundary and session_repeating:
                    self._emit_playhead(loop_start)
                    continue
                break

            finalize_tutor_session()
            return

        # Follow mode (non-wait): play events with tempo/transpose and periodic scoring
        def score_realtime() -> None:
            nonlocal last_scored_chord_idx, bar_correct, bar_total, chord_idx
            if last_scored_chord_idx < chord_idx and chords:
                completed_chords = chords[last_scored_chord_idx:chord_idx]
                if completed_chords and self.performance.events:
                    from .timeline import ExpectedMoment

                    expected_moments = [
                        ExpectedMoment(time=c.time, notes=c.notes, track_index=c.track_index, channel=c.channel)
                        for c in completed_chords
                    ]
                    results = score_performance(expected_moments, self.performance.events)
                    for result in results:
                        self.feedback_event.emit(result)
                        bar_total += 1
                        if result.verdict in {"PERFECT", "GOOD"}:
                            bar_correct += 1
                        try:
                            reward = self.gamification.apply_score([result])
                            logger.info(
                                f"Gamification (realtime): xp={reward.xp_gained} gold={reward.gold_gained} verdict={result.verdict}"
                            )
                            self.hero_changed.emit(self.gamification.hero_text(reward))
                            self.reward_awarded.emit(reward.xp_gained, reward.gold_gained)
                            try:
                                unlocked = self.gamification.check_achievements()
                                for a in unlocked:
                                    self.achievement_unlocked.emit(a.get("name", "Achievement"), a.get("description", ""))
                            except Exception:
                                pass
                            self._gamified_during_playback = True
                        except Exception:
                            pass
                    self.feedback_bar.emit(bar_correct, bar_total)
                last_scored_chord_idx = chord_idx

        self._emit_playhead(loop_start)
        while not self.stop_flag.is_set():
            n_before = self._count_chords_before(chords, loop_start)
            chord_idx = n_before
            last_scored_chord_idx = n_before
            bar_correct = 0
            bar_total = 0
            start_wall = time.perf_counter()
            if session_repeating:
                self.performance.reset()
            hit_loop_boundary = False

            for ev in self.events:
                if self.stop_flag.is_set():
                    break
                if ev.time < loop_start:
                    continue
                if loop_end and ev.time > loop_end:
                    if session_repeating:
                        hit_loop_boundary = True
                    break

                self._emit_playhead(ev.time)

                target_time = start_wall + (ev.time - loop_start) / tempo_mult
                while not self.stop_flag.is_set() and time.perf_counter() < target_time:
                    time.sleep(0.001)
                msg = ev.message.copy()
                if msg.type in {"note_on", "note_off"} and transpose:
                    msg.note = _clamp_note(msg.note + transpose)
                track_ok = True if self.learning_tracks is None else ev.track_index in self.learning_tracks
                chan_ok = self.learning_channel is None or msg.channel == self.learning_channel
                is_learning_part = track_ok and chan_ok
                if is_learning_part and msg.type == "note_on" and chord_idx < len(chords):
                    chord_idx += 1
                self.engine.send(msg)
                if chord_idx < len(chords):
                    score_realtime()

            if self.stop_flag.is_set():
                break
            if hit_loop_boundary and session_repeating:
                self._emit_playhead(loop_start)
                continue
            break

        score_realtime()
        self.status_changed.emit("Playback finished.")
        if chords:
            results = score_performance(chords, self.performance.events)
            counts = Counter(r.verdict for r in results)
            total = len(results)
            perfect = counts.get("PERFECT", 0)
            good = counts.get("GOOD", 0)
            late = counts.get("LATE", 0)
            early = counts.get("EARLY", 0)
            miss = counts.get("MISS", 0)
            wrong = counts.get("WRONG", 0)
            summary = f"Score: Perfect={perfect} Good={good} Late={late} Early={early} Miss={miss} Wrong={wrong} / {total}"
            self.score_changed.emit(summary)

            if not self._gamified_during_playback:
                try:
                    reward = self.gamification.apply_score(results)
                    logger.info(
                        f"Gamification reward: xp={reward.xp_gained} gold={reward.gold_gained} notes={reward.notes} perfect={reward.perfect} good={reward.good}"
                    )
                    self.hero_changed.emit(self.gamification.hero_text(reward))
                    self.reward_awarded.emit(reward.xp_gained, reward.gold_gained)
                    try:
                        unlocked = self.gamification.check_achievements()
                        for a in unlocked:
                            self.achievement_unlocked.emit(a.get("name", "Achievement"), a.get("description", ""))
                    except Exception:
                        pass
                except Exception:
                    pass

            insights = diagnose_performance(results, chords)
            if insights:
                insight_text = "\n".join(
                    [f"> {insight.message}\n  -> {insight.drill_suggestion}" for insight in insights]
                )
                html = f"<b>Practice Insights:</b><br>{insight_text.replace(chr(10), '<br>')}"
                self.diagnosis_changed.emit(html, True)
            else:
                self.diagnosis_changed.emit("", False)

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
        # Immediate feedback: simple OK/NO vs current expected chord
        if msg.type == "note_on" and msg.velocity > 0 and self.current_expected:
            try:
                if msg.note in self.current_expected:
                    self.feedback.error_display.setText("OK")
                    self.feedback.error_display.setStyleSheet("color: #16a34a; font-weight: bold;")
                else:
                    self.feedback.error_display.setText("NO")
                    self.feedback.error_display.setStyleSheet("color: #dc2626; font-weight: bold;")
            except Exception:
                pass

    def _set_next_expected(self, notes: set[int]) -> None:
        self.keyboard.set_expected(notes)
        self.feedback.set_next_expected(notes)

    def _set_diagnosis(self, html: str, visible: bool) -> None:
        if visible and html:
            self.diagnosis_label.setText(html)
            self.diagnosis_label.show()
        else:
            self.diagnosis_label.hide()

    def on_expected_changed(self, time_sec: float, notes: set[int]) -> None:
        expected_set = set(notes) if notes else set()
        self.current_expected = expected_set
        self.roll.highlight_expected(expected_set, time_sec)
        self.falling.highlight_expected(expected_set, time_sec)
        self.next_expected_changed.emit(expected_set)
        self.hint_enabled_changed.emit(bool(expected_set))

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
