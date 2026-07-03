@echo off
setlocal

set ROOT=%~dp0
set APP_DIR=%ROOT%cvp_tutor
set VENV_DIR=%APP_DIR%\.venv311
set PY=%VENV_DIR%\Scripts\python.exe

cd /d "%APP_DIR%"
echo [CVP Tutor] Preparing environment...

if exist "%PY%" goto deps

where uv >nul 2>nul
if %errorlevel%==0 (
  echo [CVP Tutor] Creating Python 3.11 environment with uv...
  uv venv --python 3.11 "%VENV_DIR%"
) else (
  py -3.11 -V >nul 2>nul
  if errorlevel 1 (
    echo [CVP Tutor] Python 3.11 or uv is required.
    echo [CVP Tutor] Install uv or Python 3.11 x64, then re-run this script.
    exit /b 1
  )
  echo [CVP Tutor] Creating Python 3.11 environment...
  py -3.11 -m venv "%VENV_DIR%"
)

if not exist "%PY%" (
  echo [CVP Tutor] Could not create the Python environment.
  exit /b 1
)

:deps
echo [CVP Tutor] Installing requirements...
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 (
  echo [CVP Tutor] Failed to install dependencies.
  exit /b 1
)

echo [CVP Tutor] Launching app...
"%PY%" -m cvp_tutor.app
