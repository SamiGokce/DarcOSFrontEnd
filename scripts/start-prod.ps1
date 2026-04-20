$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$backendPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    throw "Backend virtual environment not found at $backendPython. Create it with: cd backend; uv venv --python 3.10; uv pip install -r requirements.txt"
}

Write-Host "Building frontend"
Push-Location $frontend
try {
    npm run build
}
finally {
    Pop-Location
}

Write-Host "Collecting Django static files"
Push-Location $backend
try {
    $env:ENVIRONMENT = "production"
    .\.venv\Scripts\python.exe manage.py collectstatic --noinput
}
finally {
    Pop-Location
}

Write-Host "Starting Django production server on http://127.0.0.1:8000/"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$backend'; `$env:ENVIRONMENT='production'; .\.venv\Scripts\python.exe manage.py runserver 8000"
)
