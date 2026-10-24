# Roadmap & Milestones

Milestone 1 — MIDI Tutor Core (MVP)
- **UN-20261024-016-0004** Connect CVP-301 MIDI IN/OUT reliably.
- **UN-20261024-016-0005** Load MIDI files and build canonical timeline (ticks → seconds) with tempo map.
- **UN-20261024-016-0006** Present two UI modes: Piano-roll (Synthesia-like) and On-screen Keyboard.
- **UN-20261024-016-0007** Follow mode scoring and basic feedback.
- **UN-20261024-016-0008** Acceptance tests: keys show in monitor; load MIDI renders; simple scoring works.

Milestone 2 — Wait Mode + Looping
- **UN-20261024-016-0011** Implement Wait mode (advance only when expected chord/note played).
- **UN-20261024-016-0012** Loop bars and tempo scaling (slow practice).
- **UN-20261024-016-0013** Hint playback via MIDI OUT (soft notes).

Milestone 3 — Library, Profiles, Persistence
- **UN-20261024-016-0016** Song library and section markers.
- **UN-20261024-016-0017** User profiles and basic progress tracking.
- **UN-20261024-016-0018** Save session recordings (MIDI).

Milestone 4 — Diagnosis + Planner
- **UN-20261024-016-0021** Rule-based diagnosis engine (top 3 issues + drill suggestions).
- **UN-20261024-016-0022** Simple practice planner & spaced repetition.

Milestone 5 — AI Coach (optional)
- **UN-20261024-016-0025** Provide structured session summary JSON for LLM consumption.
- **UN-20261024-016-0026** LLM-based textual coaching and explanation (online/optional).

Notes:
- Ship Milestone 1 as a fast, stable desktop app (PyQt6 + mido/rtmidi recommended).
- Keep all I/O non-blocking; use worker threads for playback and MIDI processing.
- Library accelerators:
  - M1 visuals: study PyPiano (Synthesia clone) for falling-note math and hit-line timing.
  - M2 wait mode: reuse DTW from librosa or the Matchmaker score-following library to align live MIDI to score.
  - M4 diagnosis: use music21 to detect chords/keys/interval errors from PerformanceEvent streams.
  - M5 drills: MusPy to auto-generate scale/arpeggio MIDI for targeted practice.
