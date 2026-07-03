@echo off
setlocal

cd /d "%~dp0"
echo [Parris Piano Hub] Starting local web server...

where npm >nul 2>nul
if %errorlevel%==0 (
  npm start
  exit /b %errorlevel%
)

py -3 -m http.server 8080 --bind 127.0.0.1
if %errorlevel% neq 0 (
  python -m http.server 8080 --bind 127.0.0.1
)
