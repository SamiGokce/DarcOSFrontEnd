$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$backendPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    throw "Backend virtual environment not found at $backendPython. Create it with: cd backend; uv venv --python 3.10; uv pip install -r requirements.txt"
}

Write-Host "Starting Django backend on http://127.0.0.1:8000/"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$backend'; `$env:ENVIRONMENT='development'; .\.venv\Scripts\python.exe manage.py runserver 8000"
)

Write-Host "Starting Vite frontend on http://127.0.0.1:5173/"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$frontend'; npm run dev -- --host 127.0.0.1 --port 5173"
)
