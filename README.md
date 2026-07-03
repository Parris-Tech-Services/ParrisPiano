# Parris Piano App

`ParrisPianoApp` is the synced local companion copy of `../ParrisPiano`. It keeps the shared Yamaha CVP-301 practice app and desktop tutor aligned with the primary repo while preserving extra machine-specific resources and installers.

## Contents

- `index.html`, `midi-keyboard.js`, `sheet.js`, `styles.css` — shared browser practice surface
- `package.json`, `package-lock.json`, `.eslintrc.json` — browser app tooling
- `cvp_tutor/` — shared desktop tutor code and packaging files
- `docs/` — synced project docs plus local recovery notes
- `CVP301/` — local drivers, firmware, installers, and piano software
- `Desktop/` — local desktop copies and reference material
- `assets/` — local runtime assets
- `samples/` — sample recordings and local test inputs

## Quickstart

### Browser app

```powershell
npm install
npm run start
```

Then open `http://localhost:8080`.

### Desktop tutor

```powershell
cd cvp_tutor
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m cvp_tutor
```

Or use `start_cvp_tutor.bat`.

## Project role

- `ParrisPiano/` is the primary source of truth for shared code and docs.
- `ParrisPianoApp/` is the local companion copy for this machine and keeps the extra piano software folders intact.
- Shared feature work should be done in `ParrisPiano/` first, then synced here when needed.

## Documentation

See:

- `docs/README.md`
- `docs/CHANGELOG.md`
- `docs/PROJECT_STATUS.md`
- `docs/RECOVERY_NOTES.md`
