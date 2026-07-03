# Parris Piano Improvement Plan

This document collects high-impact improvements for the Parris Piano repository, including project structure, tooling, UX, testing, and feature areas.

## 1. Project structure & onboarding

- Add a root-level `README.md` that clearly separates:
  - the browser-based MIDI dashboard app
  - the Windows desktop `cvp_tutor` app
  - setup instructions for each app
  - required dependencies and prerequisites
- Add a `LICENSE` file to make the project legally reusable.
- Add a `CONTRIBUTING.md` for collaborator guidance.
- Clean up the repository layout to clearly partition web vs desktop code.

## 2. Packaging & build tooling

### Web app
- Add `package.json` for dependency and script management.
- Add a development server script (`npm start`) for local development.
- Move inline CSS and JS out of `index.html` into dedicated files.
- Add a build step or static bundling if needed for future enhancements.

### Desktop app
- Add `pyproject.toml` or a minimal packaging layout for the Python app.
- Keep `requirements.txt` but also add `requirements-dev.txt` for test/dev dependencies.
- Improve `build.ps1` to be robust and reproducible.
- Consider packaging the desktop tutor app as an installable or standalone executable.

## 3. Continuous Integration & automated tests

- Add GitHub Actions workflows for:
  - Python lint/test on `cvp_tutor`
  - Web lint/build checks for `index.html` / JS files
  - docs/README validation or markdown checks
- Expand test coverage beyond existing logic tests:
  - MIDI parsing (`midi_parse.py`)
  - timeline grouping (`timeline.py`)
  - scoring logic (`scoring.py`)
  - practice-plan generation
- Add a `Makefile` or script entrypoints for running tests and linting.

## 4. Web UI improvements

- Refactor `midi-keyboard.js` into modular components:
  - MIDI device management
  - keyboard rendering
  - scoring and practice plan
  - UI control wiring
- Separate style definitions into a dedicated stylesheet.
- Improve device handling and error states:
  - detect Web MIDI availability
  - auto-select Yamaha CVP-301 if available
  - show meaningful warnings when MIDI access is unavailable
- Improve UX:
  - clearer flow for connecting MIDI and starting practice
  - responsive layout for smaller screens
  - more accessible controls, labels, and indicators
  - richer practice plan presentation instead of plain JSON text

## 5. Feature roadmap alignment

- Prioritize core practice features in the web app:
  - live scoring / timing feedback
  - hint mode for expected chords
  - repeat-bar practice selection
- Improve parity between web and desktop experience when possible.
- Use the existing docs as the basis for milestone-driven development.

## 6. High-value next feature areas

- Wait-mode alignment using DTW or sequence matching (`librosa`, `Matchmaker`).
- Live diagnosis / music analysis using `music21`.
- Drill generation via `muspy` or custom MIDI generator.
- Export workflows: MIDI export, PDF score export, MuseScore integration.
- Practice plan automation: generate small repeat loops for weak bars.

## 7. Immediate first-phase tasks

1. Create a clear root README and add a license.
2. Add CI workflows for Python tests and web checks.
3. Refactor `index.html` and `midi-keyboard.js` to separate concerns.
4. Add a `pyproject.toml` / dev requirements for `cvp_tutor`.
5. Improve the web app MIDI device flow and error handling.

## 8. Suggested document and task files

- `docs/IMPROVEMENTS.md` (this document)
- `docs/ROADMAP.md` (existing)
- `docs/TO_DO.md` (existing)
- `docs/DEVELOPMENT.md` (added)
- `docs/README.md` (updated)
- `README.md` (root)
- `CONTRIBUTING.md`
- `LICENSE`

---

## 9. Completed documentation improvements

The following documentation and repo onboarding items have been added:
- Root `README.md` rewritten with clear web vs desktop guidance.
- `LICENSE` added (MIT).
- `CONTRIBUTING.md` added.
- `package.json` and `.eslintrc.json` added for web tooling.
- `package-lock.json` generated for deterministic web dependency management.
- `styles.css` extracted and linked from `index.html` to separate presentation from markup.
- Removed the unused `@tonejs/midi` script from `index.html` to reduce external dependency load.
- `midi-keyboard.js` refactored with cleaner MIDI initialization and device connection handling.
- MIDI controls now disable cleanly when Web MIDI is unavailable and display a clear fallback state.
- `displayPlan()` now renders generated practice plans as styled UI cards instead of raw JSON text.
- ESLint toolchain configured and auto-fix applied to `midi-keyboard.js` for consistent JS style.
- `cvp_tutor/pyproject.toml` and `requirements-dev.txt` added.
- Added `cvp_tutor` package entry point and `python -m cvp_tutor` support.
- GitHub Actions workflows added for Python tests and web linting.
- `docs/DEVELOPMENT.md` added for developer onboarding.
- `docs/README.md` updated with docs navigation.

---

This plan is intended to guide the next rounds of refactoring, packaging, and feature development. The highest-leverage work is better onboarding, CI/tests, and a cleaner web app architecture before deeper feature additions.

---

## 10. Prioritized guidance (assistant summary)

This section captures a concise prioritization for improving Parris Piano: what matters most depends on whether you focus on the **desktop tutor** (launched via `start_cvp_tutor.bat` → `python -m cvp_tutor.app` after a Python 3.11 venv and dependencies), the **browser practice hub** (`index.html` + `midi-keyboard.js`), or **both**.

### App surfaces

- **Desktop (`start_cvp_tutor.bat`)**: Ensures a venv under `%LOCALAPPDATA%\ParrisPiano\cvp_tutor_venv311`, installs from `requirements.txt`, then runs the PyQt-based tutor.
- **Web**: Web MIDI and local dev server (`npm run start`); separate codebase concerns from the desktop app.

### Highest impact

These align with sections 1–8 above and with `docs/PROJECT_STATUS.md`; they remain the right levers:

1. **Modularize the web layer** — Split `midi-keyboard.js` into focused modules (MIDI I/O, keyboard UI, scoring, practice plan). That unlocks tests, clearer bugs, and faster iteration on the browser side.

2. **Broader automated tests** — Extend coverage to MIDI parsing, timeline/grouping, scoring, and related logic; keep CI green so pedagogy and file-format changes stay safe.

3. **Polish the MIDI/device story (web)** — Clear states when Web MIDI is missing, better device selection (e.g. preferring a CVP when present), and stronger error messages reduce friction for students and teachers.

4. **Desktop packaging and stability** — Harden `build.ps1`, consider a distributable (installer or single-folder app), and document module responsibilities so the PyQt stack stays maintainable.

5. **Feature depth where it matters** — High-value directions include alignment/wait-mode (e.g. DTW), richer feedback, repeat-bar practice, exports (MIDI/PDF), and automated drills. Prefer **one** vertical slice shipped end-to-end over many half-finished features.

### Quick wins specific to `start_cvp_tutor.bat`

- **Faster repeat launches**: Skip `pip install` when `requirements.txt` has not changed (e.g. store a hash under `%LOCALAPPDATA%\ParrisPiano`) so daily startup feels instant.
- **Pin versions**: Keep `requirements.txt` pinned enough that developer machines, CI, and classroom PCs behave consistently.
- **Supportability**: Logs already live under `cvp_tutor/logs/`; exposing “open log folder” from the desktop UI helps when something fails on a student machine.

### Choosing what to do first

- **Mostly desktop / batch launcher** — Packaging, crash reporting, and tutor UX; tests around UI, MIDI I/O, and scoring.
- **Mostly browser** — Modular JS, device UX, responsive layout, accessibility.
- **Teaching workflow** — Pick one roadmap item (e.g. repeat-bar practice, hint mode, live timing feedback) and make it obvious in the UI.

For backlog detail, see also `docs/ROADMAP.md`, `docs/TO_DO.md`, and `docs/PROJECT_STATUS.md`.