# CVP Tutor (Windows, CVP-301 Companion)

A Windows desktop app to drive a Yamaha CVP-301 over USB-MIDI: play MIDI files through the piano, practice in “wait mode”, and monitor MIDI traffic. Built with Python + PyQt6 + mido/python-rtmidi.

## Features
- Detect CVP-301 MIDI in/out, monitor incoming NoteOn/Off.
- Load .mid files, select learning part by track/channel.
- Play with tempo multiplier, transpose, loop region.
- Tutor mode (wait mode): pauses until you play the expected note/chord; hint by playing softly to the CVP.
- Test tone button to confirm MIDI out.

## Quick start (dev)
```powershell
cd C:\Users\joshu\Desktop\ParrisPianoApp\cvp_tutor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pip install pyinstaller  # optional for build
python app.py
```

## Build a one-file exe
```powershell
cd C:\Users\joshu\Desktop\ParrisPianoApp\cvp_tutor
.venv\Scripts\activate
.\build.ps1
```
Result: `dist/CVP-Tutor.exe`

## Usage notes
- Connect via the USB “TO HOST” port (printer cable). Ensure the Yamaha USB-MIDI driver is installed.
- In the app: select CVP-301 ports (auto-selected if found). Click **Test Tone** to verify output.
- Tutor mode: choose the Learning Part (track/channel), enable **Tutor**, then Play. The app waits for you on learning-part notes and keeps accompaniment going (other tracks).
- Loop: set start/end seconds (end=0 means play to end).
- Transpose adjusts only NoteOn/NoteOff; controller messages are passed through unchanged.
- Logs: `logs/app.log`.

## Troubleshooting
- No ports listed: confirm driver installed; replug USB; hit **Refresh** then **Connect**.
- Double notes: disable any MIDI thru in other apps; keep Local Control ON and ensure the app does not echo input to output (it doesn’t by default).
- High latency: close DAWs that may capture the port; use wired USB direct to PC.

## Tests
Minimal logic tests live in `tests/`. Run with:
```powershell
.venv\Scripts\activate
python -m pytest
```
