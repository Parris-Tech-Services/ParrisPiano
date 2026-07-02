# Contributing to Parris Piano

Thank you for contributing! This repository contains both a browser-based MIDI practice hub and a Windows desktop tutor app.

## How to contribute

- Open an issue for bugs, feature ideas, or documentation improvements.
- Create a branch for your work, such as `feature/keyboard-ui` or `fix/midi-port-selection`.
- Keep changes focused and use clear commit messages.

## Local setup

### Web app

```powershell
cd ParrisPiano
npm install
npm run lint
```

### Desktop app

```powershell
cd ParrisPiano\cvp_tutor
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Code style

- JavaScript: use `eslint` via `npm run lint`.
- Python: keep code readable and maintainable.
- Documentation: prefer concise, actionable examples.

## Testing

Run Python tests in `cvp_tutor/tests` with `python -m pytest`.
Update tests for any behavior changes.

## Pull requests

- Describe the problem and your solution.
- Reference related issues or docs.
- Keep the PR focused on a single improvement or bug fix.
