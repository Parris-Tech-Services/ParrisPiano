# Roadmap & Milestones

Milestone 1 — MIDI Tutor Core (MVP)
- Connect CVP-301 MIDI IN/OUT reliably.
- Load MIDI files and build canonical timeline (ticks → seconds) with tempo map.
- Present two UI modes: Piano-roll (Synthesia-like) and On-screen Keyboard.
- Follow mode scoring and basic feedback.
- Acceptance tests: keys show in monitor; load MIDI renders; simple scoring works.

Milestone 2 — Wait Mode + Looping
- Implement Wait mode (advance only when expected chord/note played).
- Loop bars and tempo scaling (slow practice).
- Hint playback via MIDI OUT (soft notes).

Milestone 3 — Library, Profiles, Persistence
- Song library and section markers.
- User profiles and basic progress tracking.
- Save session recordings (MIDI).

Milestone 4 — Diagnosis + Planner
- Rule-based diagnosis engine (top 3 issues + drill suggestions).
- Simple practice planner & spaced repetition.

Milestone 5 — AI Coach (optional)
- Provide structured session summary JSON for LLM consumption.
- LLM-based textual coaching and explanation (online/optional).

Notes:
- Ship Milestone 1 as a fast, stable desktop app (PyQt6 + mido/rtmidi recommended).
- Keep all I/O non-blocking; use worker threads for playback and MIDI processing.
- Library accelerators:
  - M1 visuals: study PyPiano (Synthesia clone) for falling-note math and hit-line timing.
  - M2 wait mode: reuse DTW from librosa or the Matchmaker score-following library to align live MIDI to score.
  - M4 diagnosis: use music21 to detect chords/keys/interval errors from PerformanceEvent streams.
  - M5 drills: MusPy to auto-generate scale/arpeggio MIDI for targeted practice.
