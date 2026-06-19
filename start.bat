@echo off
setlocal enabledelayedexpansion

set ROOT=%~dp0
set BAK_WIN=KG-Backend

echo.
echo   ============================================
echo     KnowledgeGraph v2.5
echo   ============================================
echo.

echo   [Clean] Checking ports ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8013.*LISTENING"') do (
  echo          Killing PID %%a on port 8013
  taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING"') do (
  echo          Killing PID %%a on port 3000
  taskkill /PID %%a /F >nul 2>&1
)
taskkill /FI "WINDOWTITLE eq %BAK_WIN%" /F >nul 2>&1

echo.
echo   [1/2] Starting Backend (port 8013)

set BAK_CMD=%TEMP%\kg_backend.cmd
(
  echo @echo off
  echo title %BAK_WIN%
  echo cd /d "%ROOT%backend"
  echo call venv\Scripts\activate.bat
  echo echo   Backend : http://localhost:8013
  echo echo   Swagger : http://localhost:8013/docs
  echo uvicorn app.main:app --host 0.0.0.0 --port 8013 --reload --log-level info
) > "%BAK_CMD%"

start "%BAK_WIN%" "%BAK_CMD%"

echo   Waiting for backend ...
:wait_loop
timeout /t 2 /nobreak >nul
netstat -ano | findstr ":8013.*LISTENING" >nul 2>&1
if errorlevel 1 goto wait_loop
echo   Backend ready.

echo.
echo   [2/2] Starting Frontend (port 3000)
echo   http://localhost:3000
echo   Ctrl+C to stop
echo.
cd /d "%ROOT%frontend"
call npm run dev

echo.
echo   Shutting down ...
taskkill /FI "WINDOWTITLE eq %BAK_WIN%" /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8013.*LISTENING"') do (
  taskkill /PID %%a /F >nul 2>&1
)
del "%BAK_CMD%" >nul 2>&1
echo   All stopped.

pause
