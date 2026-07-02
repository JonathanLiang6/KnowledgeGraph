@echo off
title KnowledgeGraph v4.0
set ROOT=%~dp0

echo.
echo   ============================================
echo     KnowledgeGraph v4.0
echo   ============================================
echo.

echo   [Clean] Stopping old processes ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8013"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000"') do taskkill /PID %%a /F >nul 2>&1
echo          Done.

cd /d "%ROOT%backend"

echo   [Check] Python ...
if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
    echo          venv
) else (
    set PYTHON=python
    echo          system python
)

echo   [1/2] Starting Backend (port 8013)
start "KG-Backend" /MIN cmd /c "%PYTHON% -m uvicorn app.main:app --host 0.0.0.0 --port 8013 --reload --log-level info"

echo          Waiting for backend ...
:wait_backend
timeout /t 2 /nobreak >nul
netstat -ano 2>nul | findstr ":8013" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 goto wait_backend
echo          Backend ready

echo   [2/2] Starting Frontend (port 3000)
echo.
echo   ============================================
echo     http://localhost:3000
echo     Close this window to stop
echo   ============================================
echo.

cd /d "%ROOT%frontend"
call npm run dev

echo   Stopping ...
taskkill /FI "WINDOWTITLE eq KG-Backend" /F >nul 2>&1
pause
