# To Do – Tasks & Acceptance Criteria

Top-level milestones (see ROADMAP.md). Below are actionable tasks for Milestone 1 (MVP).

Milestone 1 – MVP Tasks
- [ ] `midi_io.py` – enumerate ports, auto-select CVP-301, open input/output.
  - Acceptance: device appears in UI and input events are received.
- [ ] `midi_parse.py` – load `.mid`, tempo map, ticks?seconds, extract note on/off.
  - Acceptance: loaded MIDI shows correct time positions in lesson UI.
- [ ] `timeline.py` – group notes into ExpectedMoment objects (CHORD_WINDOW_MS=40ms).
  - Acceptance: grouping correctly forms chords from close timestamps.
- [ ] `playback.py` – scheduler with tempo multiplier, loop support, mute/solo parts.
  - Acceptance: loop region plays at set tempo and sends MIDI OUT.
- [ ] `performance.py` – capture incoming notes with timestamps.
  - Acceptance: pressing keys shows timestamps in monitor within 50ms.
- [ ] `scoring.py` – implement PERFECT_MS=50, GOOD_MS=110 windows; produce per-moment ScoreEvents.
  - Acceptance: run a test song and produce per-bar aggregates.
- [ ] `ui` – implement `keyboard_view` (88 keys) and `piano_roll` toggle; transport controls.
  - Acceptance: toggle switches view, keyboard highlights expected and pressed notes.
- [ ] Immediate feedback panel: show next chord and flash ?/? on incoming notes vs expected.
- [ ] Per-bar scoring surfacing (Perfect/Good/Miss) and a "repeat bar" control for missed bars.
- [ ] Hint button that plays the expected chord softly to MIDI OUT.
- [ ] External score flow: auto-export MIDI?PDF via MuseScore, open externally; show bar/beat overlay in app.
- [ ] Diagnosis: rule-based detection (late entries, missed notes, stuck pedal) with drill suggestions.

Milestone 1 extras
- [ ] Export recorded session to `.mid`.
- [ ] CI tests: parsing/grouping/scoring unit tests.

Notes for implementation
- Keep I/O non-blocking.
- Start with strict matching as default for Wait mode, and forgiving for Follow mode.
