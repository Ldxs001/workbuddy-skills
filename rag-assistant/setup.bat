@echo off
setlocal enabledelayedexpansion
title RAG Assistant - Setup

echo ========================================
echo    RAG Assistant - Environment Setup
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python found
    python --version
    goto INSTALL_DEPS
)

:: Download Python
echo [!] Python not found, downloading...
set PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
set PY_EXE=%TEMP%\python-3.11.9-amd64.exe

where curl >nul 2>&1
if %errorlevel% equ 0 (
    curl -L -o "%PY_EXE%" "%PY_URL%" 2>nul
) else (
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('%PY_URL%', '%PY_EXE%')}" >nul 2>&1
)
if not exist "%PY_EXE%" (
    echo [FAIL] Download failed. Install Python 3.11+ from:
    echo        https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Downloaded, installing...
echo       Make sure to check "Add Python to PATH" in installer
start /wait "" "%PY_EXE%" /passive Include_test=0
del "%PY_EXE%" 2>nul

:: Refresh PATH from registry
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"
if defined USER_PATH set "PATH=%PATH%;%USER_PATH%"
ping 127.0.0.1 -n 3 >nul

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Python not found after install. Please install manually.
    pause
    exit /b 1
)
echo [OK] Python installed
python --version

:: Install dependencies
:INSTALL_DEPS
echo.
echo Installing dependencies (first time may take 5-10 min)...
python -m pip install -r "%~dp0requirements.txt" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] Some packages failed. Runtime will retry automatically.
)

echo.
echo ========================================
echo   Ready. Launching RAG Assistant...
echo ========================================

:: Start server
cd /d "%~dp0"
start /B "" python main.py

:: Wait for server to start
echo Waiting for server...
ping 127.0.0.1 -n 4 >nul

:: Open browser
start http://localhost:8765

echo.
echo Server is running at: http://localhost:8765
echo Close this window to stop the server.
echo.
