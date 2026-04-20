# DarcOS Frontend

This repository contains a React/Vite frontend and a Django backend.

## Run Modes

### Development

Development uses two processes:

- Django backend at `http://127.0.0.1:8000/`
- Vite frontend at `http://127.0.0.1:5173/`

Vite proxies `/api` and `/admin` to Django during development.

### Production

Production uses one process:

- Django at `http://127.0.0.1:8000/`

Django serves the built frontend from `frontend/dist`.

## Scripts

Use the scripts in the `scripts/` folder:

- `scripts/start-dev.ps1` starts both apps in development mode.
- `scripts/start-prod.ps1` builds the frontend, collects Django static files, and starts Django in production mode.

## Setup

### Backend

```powershell
cd backend
uv venv --python 3.10
uv pip install -r requirements.txt
```

### Frontend

```powershell
cd frontend
npm install
```

## Manual Start

### Development

```powershell
.\scripts\start-dev.ps1
```

Or run them manually:

```powershell
Set-Location backend
$env:ENVIRONMENT = "development"
.\.venv\Scripts\python.exe manage.py runserver 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### Production

```powershell
.\scripts\start-prod.ps1
```

Or run them manually:

```powershell
Set-Location frontend
npm run build
```

```powershell
Set-Location backend
$env:ENVIRONMENT = "production"
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver 8000
```

## Notes

- Development mode depends on the frontend dev server proxying backend requests.
- Production mode only needs `http://127.0.0.1:8000/`.
- If you change frontend code in production mode, rebuild the frontend before restarting Django.
