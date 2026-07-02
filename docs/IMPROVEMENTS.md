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