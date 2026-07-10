@echo off
setlocal enabledelayedexpansion
title Orchestrator

echo ========================================
echo    Orchestrator - Setup
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python found
    goto START
)
echo [FAIL] Python not found. Install Python 3.11+
pause
exit /b 1

:START
echo Installing dependencies...
python -m pip install -r "%~dp0requirements.txt" 2>nul
echo.

cd /d "%~dp0"

:: Clean up old files
if exist "%~dp0server.pid" del "%~dp0server.pid" 2>nul
if exist "%~dp0server.port" del "%~dp0server.port" 2>nul

:: Kill any process still on our old port
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8765 " 2^>nul') do taskkill /f /pid %%a >nul 2>&1

:: Start server (auto port, background)
start /B "" python main.py --web --port auto --pidfile "%~dp0server.pid"

:: Wait for server.port (up to 15s)
set WAIT=0
:WAIT_LOOP
if exist "%~dp0server.port" goto PORT_FOUND
ping 127.0.0.1 -n 2 >nul
set /a WAIT+=2
if %WAIT% lss 15 goto WAIT_LOOP
echo [WARN] Server not ready, opening http://localhost:8765...
start http://localhost:8765
goto RUNNING

:PORT_FOUND
set /p PORT=<"%~dp0server.port"
echo Server started on port: !PORT!
start http://localhost:!PORT!

:RUNNING
echo.
echo ========================================
echo  Server is running.
echo  Press any key to STOP the server and exit.
echo ========================================
pause >nul

:: Stop server & cleanup
echo Stopping server...
if exist "%~dp0server.pid" (
    set /p SPID=<"%~dp0server.pid"
    taskkill /f /pid !SPID! >nul 2>&1
    del "%~dp0server.pid" 2>nul
)
if exist "%~dp0server.port" del "%~dp0server.port" 2>nul
echo Server stopped.
