# Changelog

This changelog records the repo-level improvements made during the recent update cycle.

## 2026-04-11

- Root `README.md` rewritten with a clear web app and desktop app overview.
- Added `LICENSE` (MIT) for open source reuse.
- Added `CONTRIBUTING.md` for contributor onboarding.
- Added `package.json` and `.eslintrc.json` for the browser app toolchain.
- Generated `package-lock.json` to lock web dependencies.
- Extracted inline CSS from `index.html` into `styles.css`.
- Added `cvp_tutor/pyproject.toml` and `cvp_tutor/requirements-dev.txt` for Python packaging and dev dependencies.
- Added GitHub Actions workflows:
  - `.github/workflows/python-tests.yml`
  - `.github/workflows/web-checks.yml`
- Added `docs/DEVELOPMENT.md` for developer setup and workflow guidance.
- Added styled practice plan rendering in `midi-keyboard.js` and improved UI output for generated drill loops.
- Installed and configured the web app ESLint toolchain, then auto-fixed `midi-keyboard.js` formatting.
- Added `docs/PROJECT_STATUS.md` as a progress summary.
- Updated `docs/README.md` with docs navigation and added the new status page.
- Removed an unused `@tonejs/midi` script tag from `index.html`.
- Added MIDI control disable state handling for unsupported or unavailable Web MIDI.
- Added `cvp_tutor` package entry point and `python -m cvp_tutor` support.
- Updated `docs/IMPROVEMENTS.md` to reflect completed documentation and tooling improvements.
- Recovered this repo from a corrupted `.git` directory by moving the broken metadata aside and reinitializing a clean Git repository.
- Synced the shared web app, Python tutor tooling, and documentation from `../ParrisPiano`.
- Re-aligned `index.html`, `midi-keyboard.js`, and `sheet.js` with the merged shared web surface after promoting the richer notation import workflow into the primary repo.
- Added `docs/RECOVERY_NOTES.md` to document the backup path, preserved local assets, and future sync workflow.
