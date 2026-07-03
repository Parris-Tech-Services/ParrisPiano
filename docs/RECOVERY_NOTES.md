# Recovery Notes

## 2026-04-11

This folder was repaired as a synced companion copy of `../ParrisPiano`.

What changed:
- The damaged `.git` directory was moved aside and replaced with a fresh Git repository.
- The broken Git backup was preserved at `../ParrisPianoApp.git-broken-backup-20260411-214429`.
- The shared web app surface was synced from `ParrisPiano`:
  - `index.html`
  - `midi-keyboard.js`
  - `sheet.js`
  - `styles.css`
  - `package.json`
  - `.eslintrc.json`
- The shared desktop tutor tooling was synced from `ParrisPiano`:
  - `start_cvp_tutor.bat`
  - `cvp_tutor/build.ps1`
  - `cvp_tutor/pyproject.toml`
  - `cvp_tutor/requirements*.txt`
  - `cvp_tutor/uv.lock`
  - `cvp_tutor/tests/`
- Project documentation and contributor files were synced from `ParrisPiano`.

What was preserved:
- `CVP301/`
- `Desktop/`
- `assets/`
- `samples/`
- existing `cvp_tutor/` working files that were not part of the shared sync target

Current working model:
- `ParrisPiano/` is the primary source of truth for shared code and docs.
- `ParrisPianoApp/` is the local companion copy that keeps extra piano software, installers, and reference material.

Recommended workflow:
1. Make shared feature or bug-fix work in `ParrisPiano/`.
2. Sync only the shared files into `ParrisPianoApp/` when you want the local companion copy refreshed.
3. Keep machine-specific binaries and CVP-301 resources only in `ParrisPianoApp/`.
