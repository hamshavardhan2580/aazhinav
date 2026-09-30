@echo off
title AazhiNav AI — Stopper

echo.
echo  ================================================
echo    AazhiNav AI — Stopping All Services
echo  ================================================
echo.

:: ── Kill uvicorn / Python backend on port 8000 ───
echo  [1/2] Stopping FastAPI Backend (port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F > nul 2>&1
)

:: Also close any terminal window titled AazhiNav-Backend
taskkill /FI "WINDOWTITLE eq AazhiNav-Backend" /F > nul 2>&1

echo     Backend stopped.

:: ── Kill Vite / Node frontend on port 5173 ───────
echo  [2/2] Stopping React Frontend (port 5173)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F > nul 2>&1
)

:: Also close any terminal window titled AazhiNav-Frontend
taskkill /FI "WINDOWTITLE eq AazhiNav-Frontend" /F > nul 2>&1

echo     Frontend stopped.

echo.
echo  ================================================
echo    All AazhiNav AI services have been stopped.
echo  ================================================
echo.
pause
