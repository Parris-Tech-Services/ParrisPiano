@echo off
setlocal
set ROOT=%~dp0
cd /d "%ROOT%"
echo [CVP Tutor] Preparing environment...

REM Prefer Python 3.11 (python-rtmidi ships wheels there; newer versions will fail to build).
set PY_CMD=
for /f "tokens=2 delims= " %%v in ('py -3.11 -V 2^>nul') do (
  set PY_CMD=py -3.11
)
if not defined PY_CMD (
  echo [CVP Tutor] Python 3.11 not found. Install Python 3.11 x64 from:
  echo [CVP Tutor] https://www.python.org/downloads/release/python-3110/
  echo [CVP Tutor] Check "Add Python to PATH", then re-run this script.
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  set PY=".venv\Scripts\python.exe"
) else (
  echo [CVP Tutor] Creating virtual environment with %PY_CMD%...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [CVP Tutor] Could not create venv. Install Python 3.11 and try again.
    exit /b 1
  )
  set PY=".venv\Scripts\python.exe"
)

echo [CVP Tutor] Installing requirements (first run may take a minute)...
%PY% -m pip install --upgrade pip >nul
REM Only install if not already satisfied
%PY% -m pip install -r cvp_tutor\requirements.txt --disable-pip-version-check
if errorlevel 1 (
  echo [CVP Tutor] Failed to install dependencies. Ensure Python 3.11 is installed.
  exit /b 1
)

echo [CVP Tutor] Launching app...
%PY% -m cvp_tutor.app
