# Development Guide

This guide describes how to work on the Parris Piano repository, including the web practice hub and the CVP Tutor desktop app.

## Repository structure

- `index.html` — browser-based MIDI practice hub.
- `midi-keyboard.js` — browser MIDI handling, UI state, scoring, and practice plan logic.
- `cvp_tutor/` — Python desktop tutor app using PyQt6, mido, and python-rtmidi.
- `docs/` — project documentation, roadmap, architecture, and improvement plan.

## Setup

### Web app

1. Install Node.js.
2. From the repo root:
   ```powershell
   cd ParrisPiano
   npm install
   npm run start
   ```
3. Open `http://localhost:8080` in a browser that supports Web MIDI (Chrome/Edge).

### Desktop app

1. Install Python 3.10+.
2. From `cvp_tutor`:
   ```powershell
   cd ParrisPiano\cvp_tutor
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m cvp_tutor
   ```

3. Optionally install as an editable package:
   ```powershell
   python -m pip install -e .
   cvp_tutor
   ```
3. To install development dependencies:
   ```powershell
   python -m pip install -r requirements-dev.txt
   ```

## Running tests

### Python tests

From `cvp_tutor`:
```powershell
python -m pytest tests
```

### Web lint

From the repo root:
```powershell
npm run lint
```

### Web tests

From the repo root:
```powershell
npm test
```

## CI workflows

- `python-tests.yml` runs Python tests on GitHub Actions.
- `web-checks.yml` runs JavaScript linting.

## Recommended workflow

1. Create a feature branch.
2. Run the relevant local setup before editing code.
3. Add or update docs when behavior, APIs, or project structure changes.
4. Run tests and linting before committing.

## Notes

- The web app currently depends on local host serving because browser MIDI may be restricted on file URLs.
- The desktop tutor app currently targets Windows, but the codebase is organized so cross-platform compatibility can be added later.
- `docs/IMPROVEMENTS.md` contains current work items and improvement recommendations.
