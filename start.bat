@echo off
title AazhiNav AI — Launcher

echo.
echo  ================================================
echo    AazhiNav AI — Starting All Services
echo  ================================================
echo.

:: ── Start FastAPI Backend ────────────────────────
echo  [1/2] Starting FastAPI Backend on port 8000...
start "AazhiNav-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak > nul

:: ── Start React Frontend ─────────────────────────
echo  [2/2] Starting React Frontend on port 5173...
start "AazhiNav-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo  ================================================
echo    Both services are starting up!
echo.
echo    Backend  →  http://localhost:8000
echo    API Docs →  http://localhost:8000/docs
echo    Frontend →  http://localhost:5173
echo  ================================================
echo.

:: Wait for frontend to start then open browser
timeout /t 5 /nobreak > nul
start "" "http://localhost:5173"

echo  Browser opened. Press any key to close this window.
pause > nul
