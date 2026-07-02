param(
    [string]$Python = ".venv\\Scripts\\python.exe"
)

if (-not (Test-Path $Python)) {
    Write-Host "Python not found at $Python. Activate your venv or pass -Python path." -ForegroundColor Yellow
    exit 1
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt pyinstaller

Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

& $Python -m PyInstaller `
    --noconfirm `
    --name "CVP-Tutor" `
    --onefile `
    --add-data "assets;assets" `
    app.py

Write-Host "Build complete. See dist\\CVP-Tutor.exe" -ForegroundColor Green
