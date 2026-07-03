## Architecture Summary

Overview:
- Desktop app (Windows) that separates concerns into: MIDI I/O, MIDI parsing, timeline/expected moments, playback scheduler, performance capture, scoring, tutor state machine, diagnosis/planner, and UI views.

Suggested modules (Python/PyQt6 layout):
- `cvp/midi_io.py` — enumerate ports, auto-select CVP-301, open input/output, emit events.
- `cvp/midi_parse.py` — load `.mid` files, build tempo map, convert ticks→seconds, extract note events.
- `cvp/timeline.py` — group notes into ExpectedMoment objects (chord grouping window).
- `cvp/playback.py` — scheduler for MIDI OUT with tempo multiplier and looping.
- `cvp/performance.py` — capture incoming performance events with timestamps.
- `cvp/scoring.py` — match expected vs played using timing windows and produce ScoreEvents.
- `cvp/tutor.py` — Follow and Wait modes state machine.
- `cvp/diagnosis.py` & `cvp/planner.py` — rule-based insights and practice plan generation.

UI:
- `ui/main_window.py` — host tabs: Library, Lesson, Progress, Settings.
- `ui/widgets/keyboard_view.py` — 88-key painter; highlights expected/pressed/wrong keys.
- `ui/widgets/piano_roll.py` — QGraphics-based scrolling notes.
- `ui/widgets/transport.py` — play/stop, tempo, loop, transpose.

Threading/Concurrency:
- MIDI callbacks and playback scheduler must not block the UI thread.
- Use worker threads or asyncio workers for scheduler and heavy processing.

Data models:
- `MidiNoteEvent`, `ExpectedMoment`, `PerformanceEvent`, `ScoreEvent`, `Section`, `UserProfile`, `SessionSummary` (see mega-prompt for fields).

Testing:
- Unit tests for parsing, grouping, and scoring.
- Integration test that uses a recorded MIDI file and a simulated input stream.
