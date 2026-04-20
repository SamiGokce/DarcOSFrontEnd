# Scripts

This folder contains helper scripts for starting the app in development or production mode.

## `start-dev.ps1`

Starts both apps:

- Django backend on `http://127.0.0.1:8000/`
- Vite frontend on `http://127.0.0.1:5173/`

## `start-prod.ps1`

Builds the frontend, collects static files, and starts Django on `http://127.0.0.1:8000/`.

## Requirements

- PowerShell 5+
- Backend virtual environment at `backend/.venv`
- Frontend dependencies installed in `frontend/node_modules`
