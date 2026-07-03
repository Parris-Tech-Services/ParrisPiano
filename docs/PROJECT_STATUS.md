# Project Status

This document summarizes the current status of the Parris Piano repository and the most important next steps.

## Completed

- Root repo documentation improved with a clean `README.md`.
- License added (`LICENSE` MIT).
- Contributor onboarding added (`CONTRIBUTING.md`).
- Web tooling scaffolding added: `package.json`, `.eslintrc.json`, `package-lock.json`.
- `styles.css` added and the inline CSS was moved from `index.html` into a dedicated stylesheet.
- Desktop Python packaging metadata added: `cvp_tutor/pyproject.toml`.
- Desktop dev dependencies file added: `cvp_tutor/requirements-dev.txt`.
- GitHub Actions workflows added:
  - `.github/workflows/python-tests.yml`
  - `.github/workflows/web-checks.yml`
- Docs navigation improved: `docs/README.md`, `docs/DEVELOPMENT.md`, `docs/IMPROVEMENTS.md`.

## In progress / remaining

- Refactor web app source structure: split `midi-keyboard.js` into modules.
- Improve web app UI and MIDI error handling.
- Add Python linting and broader test coverage.
- Build the desktop tutor app packaging and stability improvements.
- Complete the `docs/TO_DO.md` backlog and wire it to engineering work.

## Highest priority next steps

1. Refactor and modularize the browser MIDI app.
2. Add test coverage for MIDI parsing, timeline grouping, and scoring.
3. Improve the web app device flow and provide better failure messages.
4. Add a local development server and package-lock support.
5. Add a more complete desktop app architecture doc with module mappings.

## References

- `docs/IMPROVEMENTS.md`
- `docs/TO_DO.md`
- `docs/ROADMAP.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
