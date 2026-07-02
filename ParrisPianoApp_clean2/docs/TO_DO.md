# To Do - Tasks & Acceptance Criteria

Top-level milestones (see ROADMAP.md). Below are actionable tasks for Milestone 1 (MVP).

Milestone 1 - MVP Tasks
- [ ] `midi_io.py` - enumerate ports, auto-select CVP-301, open input/output.
  - Acceptance: device appears in UI and input events are received.
- [ ] `midi_parse.py` - load `.mid`, tempo map, ticks->seconds, extract note on/off.
  - Acceptance: loaded MIDI shows correct time positions in lesson UI.
- [ ] `timeline.py` - group notes into ExpectedMoment objects (CHORD_WINDOW_MS=40ms).
  - Acceptance: grouping correctly forms chords from close timestamps.
- [ ] `playback.py` - scheduler with tempo multiplier, loop support, mute/solo parts.
  - Acceptance: loop region plays at set tempo and sends MIDI OUT.
- [ ] `performance.py` - capture incoming notes with timestamps.
  - Acceptance: pressing keys shows timestamps in monitor within 50ms.
- [ ] `scoring.py` - implement PERFECT_MS=50, GOOD_MS=110 windows; produce per-moment ScoreEvents.
  - Acceptance: run a test song and produce per-bar aggregates.
- [ ] `ui` - implement `keyboard_view` (88 keys) and `piano_roll` toggle; transport controls.
  - Acceptance: toggle switches view, keyboard highlights expected and pressed notes.
- [ ] Immediate feedback panel: show next chord and flash OK/NO on incoming notes vs expected.
- [ ] Per-bar scoring surfacing (Perfect/Good/Miss) and a "repeat bar" control for missed bars.
- [ ] Hint button that plays the expected chord softly to MIDI OUT.
- [ ] External score flow: auto-export MIDI/PDF via MuseScore, open externally; show bar/beat overlay in app.
- [ ] Diagnosis: rule-based detection (late entries, missed notes, stuck pedal) with drill suggestions.

Milestone 1 extras
- [ ] Export recorded session to `.mid`.
- [ ] CI tests: parsing/grouping/scoring unit tests.


**Module Integration Checklist**

Below are concrete tasks that map each major dependency/module to actionable integrations, tests, and UI hooks so every library in the project is used to its fullest potential.

- **PyQt6:**
  - **UI wiring:** Ensure every new feature has a non-blocking UI control (buttons, toggles, progress indicators).
  - **Signals/tests:** Add unit tests for signal emissions (playback start/stop, expected_changed, hero_changed).
  - **Accessibility:** Add accessible names for critical widgets and keyboard navigation tests.

- **mido + python-rtmidi:**
  - **Device resilience:** Implement auto-reconnect and user-visible device status.
  - **High-resolution capture:** Verify `PerformanceCapture` timestamps and add unit tests for precise deltas.
  - **MIDI export/import:** Centralize export helpers (`PerformanceCapture.export_midi`) and test round-trip of recorded takes.

- **loguru:**
  - **Structured logging:** Add contextual loggers for subsystems (midi, scoring, gamification) and an on/off verbose toggle.
  - **Log rotation:** Ensure logs rotate and can be redacted for privacy before sharing.

- **music21 / muspy / pretty_midi / miditoolkit / pypianoroll:**
  - **Score conversion tests:** Round-trip MIDI → MusicXML → PDF and validate page count/measure mapping.
  - **Piano-roll export:** Add a task to export high-resolution piano-roll images for session reports.
  - **Generator utilities:** Use MusPy to generate drills and example exercises for drill-generation feature.

- **librosa / soundfile / soxr:**
  - **Audio feature extraction:** Add tempo/onset detection tasks used by DTW alignment and diagnostics.
  - **Audio-backed scoring:** Prototype an alignment pass that uses audio features when MIDI input is noisy.

- **dtw-python:**
  - **Alignment spike:** Add an integration task: align performance timing to score (handle tempo drift) and test on 5 sample MIDIs.
  - **Fallback logic:** Add unit tests for alignment failures and timeouts.

- **numpy / scipy / numba / joblib / scikit-learn:**
  - **Feature pipelines:** Create a feature-extraction module (timing, velocity, onset intervals) with tests and caching.
  - **Model tasks:** Prototype simple classifiers for difficulty/genre labeling and clustering of common errors.

- **matplotlib / pillow:**
  - **Reports:** Add a report generator (PDF/PNG) that includes timing histograms and velocity heatmaps.
  - **Thumbnails:** Generate score and piano-roll thumbnails for the library UI.

- **PyYAML / bidict / requests / tqdm:**
  - **Config files:** Move tunables (reward tables, encounter tables, level curve) into YAML and add validation tests.
  - **Remote assets:** Add a guarded task to fetch optional cloud content with progress indicators (use `requests` + `tqdm`).

- **General integration tasks:**
  - **Dependency audit:** Add a task to identify unused packages and document why each package is required.
  - **CI tests:** Add small CI jobs that run lightweight feature tests (parse sample MIDIs, run scoring, export take). 
  - **Docs:** Update `docs/TO_DO.md` and `README.md` with one-line examples showing how each module is exercised in the app.

Add these as tracked subtasks for Milestone 2 and mark owners/ETA once you pick priorities.
- Start with strict matching as default for Wait mode, and forgiving for Follow mode.

Additional ideas/upgrades
- [ ] Smart loop finder: auto-suggest practice loops around bars with the highest error density.
- [ ] Velocity coaching: show per-note dynamics targets and flag over/under hammered notes.
- [ ] Hands-separate trainer: auto-mute one hand and guide the other, then swap.
- [ ] Swing and groove coach: detect swing ratio and microtiming; give tips to tighten feel.
- [ ] Progression practice: generate chord progressions in chosen key and tempo with live scoring.
- [ ] Playlist/queue: preload multiple MIDIs and step through them without reopening files.
- [ ] Practice timer + rest prompts: Pomodoro-style sessions with cooldown stretches.
- [ ] Export performance report: PDF/CSV summary with timing/dynamics charts per session.
- [ ] Cloud/USB backup of settings and song metadata for moving between machines.
- [ ] Accessibility focus: screen reader labels on controls and keyboard-only navigation.

Future features
- [ ] Guided duet mode: split parts between student and teacher and score interplay.
- [ ] AI accompanist: generate adaptive accompaniment that follows your timing and dynamics.
- [ ] Left-hand comping coach: detect stride/walking bass vs. root-only playing and prompt upgrades.
- [ ] Rhythm sight-reading drills: random rhythm-only exercises with clap detection via MIDI pads.
- [ ] Ear-first mode: hide notes until you play them correctly by ear.
- [ ] Tempo map editor: edit rubato curves and ritardando/accelerando points on a timeline.
- [ ] Finger independence drills: targeted trill/tremolo and repeated-note exercises with timing targets.
- [ ] Phrase looping: let users loop musical phrases (not just bars) via score selection.
- [ ] Ornament coach: detect and grade trills/turns/mordents for Baroque pieces.
- [ ] Video overlay: optional webcam overlay to pair hand posture footage with MIDI analysis.

Future upgrades
- [ ] Better MIDI device resilience: auto-reconnect on USB dropouts without app restart.
- [ ] Low-latency audio path: ASIO/WASAPI-exclusive selection with round-trip latency readout.
- [ ] Theme editor: user-editable theme JSONs and live preview, export/import presets.
- [ ] Multi-profile support: per-learner profiles with personal history and difficulty settings.
- [ ] Localization: i18n for UI strings and right-to-left layout support where needed.
- [ ] Cloud score library sync: keep scores, loops, and annotations across devices.
- [ ] Mobile companion: metronome/remote control app to trigger play/stop/loop from a phone.
- [ ] Advanced logging toggle: detailed MIDI/engine traces with redaction for privacy.
- [ ] Backup/restore command: one-click export of settings/logs/MIDIs for support tickets.
- [ ] Install/update checker: in-app check for new builds and optional auto-update toggle.

Groq-powered features
- [ ] Natural-language practice coach: conversational “how do I fix bar 12?” queries answered with drill suggestions tied to session data.
- [ ] On-device lesson plans: LLM builds adaptive weekly plans from your goals, recent scores, and available time slots.
- [ ] Style transfer tips: ask “make this more jazzy/baroque” and get voicing/rhythm tweaks plus MIDI transformations.
- [ ] Finger/hand suggestions: LLM suggests fingerings per passage based on difficulty and hand span metadata.
- [ ] Mistake explainer: “why was that wrong?” produces plain-English breakdown referencing timing/dynamics/pedal traces.
- [ ] Arrangement helper: request simpler/harder versions of a piece; LLM revoices chords and trims ornaments automatically.
- [ ] Ear-training prompts: LLM generates call-and-response intervals/chords and adapts difficulty live.
- [ ] Contextual tooltips: hover a control to get LLM-generated examples and best practices tailored to the current song.
- [ ] Practice narrative: LLM writes short encouragements and insights after each session using the performance log.
- [ ] Queryable history: natural-language search over past sessions (“show my progress on arpeggios last month”).

Groq-powered upgrades
- [ ] Fast score annotation: LLM adds rehearsal marks, dynamics, and phrasing suggestions directly onto the score.
- [ ] Auto loop labeling: detect tough phrases and label loops with human-friendly summaries (“left-hand jumps, bar 18-20”).
- [ ] Intelligent defaults: LLM selects devices, tempo, and hint mode based on user profile and recent context.
- [ ] One-shot MIDI tagging: bulk-tag library by genre, key, difficulty, and mood via LLM classification.
- [ ] Guided onboarding: conversational setup flow that configures MIDI, latency, and learning goals.
- [ ] In-app changelog explainer: LLM summarizes new features in plain English with quick-start tips.
- [ ] Error recovery chat: when an exception occurs, offer LLM-suggested fixes and safe retries.
- [ ] Practice script generator: LLM crafts scripted routines (warmup → drills → repertoire) using current repertoire metadata.
- [ ] Score diff explainer: when comparing two takes/versions, LLM narrates the musical differences and suggests focus areas.
- [ ] Multimodal help: attach screenshot/log snippets and ask the LLM for troubleshooting guidance.

DnD 5e-themed features
- [ ] XP per note: every accurate note grants XP; streaks give advantage dice and level-ups unlock cosmetic auras.
- [ ] Monster encounters: practice sessions spawn monsters tied to bars; flawless bars deal damage, misses heal the foe.
- [ ] Spellcasting by chord: play specific chord recipes to trigger buffs (haste = clean triplets, shield = sustained triads).
- [ ] Adventure map: progress through a campaign map; each song is a dungeon room with optional side quests.
- [ ] Loot drops: rare “magic items” (skins, themes, soundfonts) drop on crit streaks or boss defeats.
- [ ] Party mode: cooperative duets where each player handles a “class” (melody wizard, rhythm fighter) with shared HP.
- [ ] Quest log: daily/weekly quests (e.g., “land 20 perfect notes with pedal”) with gold and XP rewards.
- [ ] Skill checks: timed mini-games framed as checks (Performance, Sleight of Hand) using your current MIDI loop.
- [ ] Boss phases: multi-phase boss fights tied to song sections; tempo ramps or key changes as “lair actions.”
- [ ] Familiar companion: a pet dragonling that reacts to your dynamics and gives hints when you’re low on HP.

DnD 5e-themed upgrades
- [ ] Class progression: choose Bard/Fighter/Rogue-style trees that unlock practice perks (better hints, wider crit window).
- [ ] Inspiration mechanic: “inspiration” points for creative phrasing; cash them in to reroll a bad bar.
- [ ] Item crafting: fuse duplicate loot into upgraded skins/FX via a “forge” UI after sessions.
- [ ] Encounter pacing: AI tunes monster HP/damage based on your recent accuracy so fights feel fair.
- [ ] Spellbook UI: in-app reference showing which chord shapes cast which spells, with quick preview playback.
- [ ] Dungeon announcer: dynamic narration (LLM) that calls out crits, fumbles, and phase changes.
- [ ] Rest system: “short/long rest” timers that recommend stretch breaks and reset buffs.
- [ ] Status effects: missed notes inflict “poison/slow” debuffs on your score meter; clean bars cleanse them.
- [ ] Campaign save slots: multiple campaign runs with separate gear, quests, and difficulty.
- [ ] Leaderboard tavern: compare campaign progress with friends; weekly raid featuring a shared boss MIDI.

DnD groundwork / backend
- [ ] Player profile + persistence: profile store (JSON/SQLite) with XP, level, gold/loot, class, quest progress, cosmetics; separate from session logs.
- [ ] Event bus/telemetry: lightweight game-event emitter (note_hit, note_miss, bar_cleared, streak_n, boss_phase_change) decoupled from UI threads.
- [ ] Reward pipeline: service converting performance events into XP/gold/loot via tunable data tables (crit thresholds, streak multipliers).
- [ ] Session/quest state: per-session state machine tracking encounter HP, boss phases, quest counters; emits updates for game overlay.
- [ ] Deterministic RNG: seedable RNG for loot/encounters to reproduce results for debugging/leaderboards.
- [ ] Content schemas: JSON for spells/monsters/items with requirements (chord, streak, tempo), effects (buffs/visuals), and flavor text.
- [ ] Overlay channel: non-blocking signal/slot path for HUD elements (HP, buffs, loot drops) separate from main piano UI updates.
- [ ] Saves/checkpoints: persistence hooks to save campaign progress after sessions and recover cleanly on crash.
- [ ] Balancing hooks: config flags to scale encounter difficulty based on accuracy/tempo history.
- [ ] Telemetry toggle: user-visible toggle to enable/disable tracking; keep logs lightweight.
- [ ] First spike: wire “performance_event -> XP/gold” service to scoring events, persist profile, and render minimal HUD (XP/level + encounter HP).
