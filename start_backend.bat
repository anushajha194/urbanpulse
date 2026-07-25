@echo off
title UrbanPulse Backend Launcher
echo ===================================================
echo   URBANPULSE BACKEND SERVICES LAUNCHER
echo ===================================================
echo.

:: 1. Boot up Docker infrastructure (PostgreSQL/PostGIS, Redis, MinIO)
echo [1/3] Spinning up Docker containers (DB, Redis, S3)...
docker compose up -d
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Docker compose failed to run. Ensure Docker Desktop is active.
    echo Services will run in fallback/offline mode.
    echo.
) else (
    echo Docker containers are active.
)
echo.

:: 2. Setup virtual environments and install dependencies
echo [2/3] Preparing virtual environments...

set SERVICES=ingestion-api detection-service dedup-service scoring-service routing-service notification-service verification-service

for %%s in (%SERVICES%) do (
    echo Processing services/%%s...
    if not exist "services\%%s\venv" (
        echo Creating virtual environment for %%s...
        python -m venv services\%%s\venv
        services\%%s\venv\Scripts\pip install -r services\%%s\requirements.txt
    )
)
echo All virtual environments prepared.
echo.

:: 3. Spawn each service in a new command terminal window
echo [3/3] Launching backend microservices...

:: Ingestion API (Port 8001)
start "UrbanPulse Ingestion API" cmd /k "cd services\ingestion-api && venv\Scripts\activate && uvicorn app.main:app --port 8001"

:: Detection Worker
start "UrbanPulse Detection Worker" cmd /k "cd services\detection-service && venv\Scripts\activate && python -m app.main"

:: Deduplication Worker
start "UrbanPulse Dedup Worker" cmd /k "cd services\dedup-service && venv\Scripts\activate && python -m app.main"

:: Scoring Worker
start "UrbanPulse Scoring Worker" cmd /k "cd services\scoring-service && venv\Scripts\activate && python -m app.main"

:: Routing + SLA Worker
start "UrbanPulse Routing Worker" cmd /k "cd services\routing-service && venv\Scripts\activate && python -m app.main"

:: Notification Worker
start "UrbanPulse Notification Worker" cmd /k "cd services\notification-service && venv\Scripts\activate && python -m app.main"

:: Verification API (Port 8002)
start "UrbanPulse Verification API" cmd /k "cd services\verification-service && venv\Scripts\activate && uvicorn app.main:app --port 8002"

echo.
echo All backend services spawned in separate terminal windows!
echo ===================================================
pause
