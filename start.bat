@echo off
echo =============================================
echo   Socratic Ed-Forge — Starting Services
echo =============================================

:: Start FastAPI backend in background
echo [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "Ed-Forge Backend" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m uvicorn backend.server:app --reload --port 8000"

:: Wait a moment for backend to be ready
timeout /t 2 /nobreak >nul

:: Start React frontend
echo [2/2] Starting React frontend on http://localhost:5173 ...
start "Ed-Forge Frontend" cmd /k "cd /d %~dp0frontend-react && npm run dev"

echo.
echo =============================================
echo   Open: http://localhost:5173
echo =============================================
