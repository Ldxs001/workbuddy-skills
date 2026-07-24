@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RAG Assistant - Setup

echo ========================================
echo    RAG Assistant - Environment Setup
echo ========================================
echo.

:: ── 版本检测与 HNSW 迁移提示 ───────────────────────
set INIT_FILE=%~dp0rag_assistant\__init__.py
set KILL_FILE=%~dp0data\.no_hnsw_prompt

:: 读取当前版本号
set CURR_VER=
for /f "tokens=2 delims=^= " %%a in ('type "%INIT_FILE%" 2^>nul ^| findstr /b "__version__"') do set CURR_VER=%%a
set CURR_VER=%CURR_VER:"=%
if "%CURR_VER%"=="" set CURR_VER=2.0.0b1

:: 取主版本号
for /f "tokens=1 delims=.b-" %%m in ("%CURR_VER%") do set CURR_MAJOR=%%m

:: ≥2.x 且未永久跳过 → 弹交互（不要用 else if，不用括号内标签）
if "%CURR_MAJOR%"=="1" goto SKIP_HNSW
if exist "%KILL_FILE%" goto SKIP_HNSW

echo.
echo ============================================================
echo  *** 检测到 2.x 及以上版本 - HNSW 索引引擎已更换
echo.
echo   当前版本: %CURR_VER%
echo   从 1.x 升级到此版本需要重建全部知识库的 HNSW 索引。初次使用的非升级用户建议直接跳过(N)。
echo.
echo   选择 N 后可通过以下途径重建:
echo     [1] 手动: 在 Web 配置页点击每个 KB 的 [HNSW] 按钮
echo     [2] API: POST /api/kb/rebuild-hnsw {"kb_name": "xxx"}
echo     [3] 自动: 首次搜索该 KB 时自动触发懒重建
echo.
echo   输入 K 则将当前版本写入标记，永久跳过此提示
echo.

:ASK_HNSW
set /p REBUILD_CHOICE="是否自动重建全部 HNSW 索引？(Y/N/K): "
if /i "!REBUILD_CHOICE!"=="Y" goto DO_REBUILD
if /i "!REBUILD_CHOICE!"=="N" goto SKIP_REBUILD
if /i "!REBUILD_CHOICE!"=="K" goto KILL_PROMPT
echo 请输入 Y / N / K
goto ASK_HNSW

:DO_REBUILD
echo.
echo 正在评估 HNSW 索引状态...
python "%~dp0estimate_rebuild_time.py"
echo.
echo 正在重建全部 HNSW 索引，请耐心等待...
python "%~dp0rebuild_all_hnsw.py" 2>&1
echo.
echo [OK] HNSW 重建完成
goto SKIP_HNSW

:SKIP_REBUILD
echo.
echo [i] 已跳过 HNSW 重建，将在首次搜索时自动触发懒重建。
goto SKIP_HNSW

:KILL_PROMPT
echo %CURR_VER%>"%KILL_FILE%"
echo.
echo [i] 已标记永久跳过。如需重新启用，删除 %KILL_FILE%

:SKIP_HNSW

:: ── 安装依赖 ─────────────────────────────────────

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
python -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [WARN] 部分包安装失败 — 请手动执行: python -m pip install -r "%~dp0requirements.txt"
    echo        错误详情请查看上方输出
)

echo.
echo ========================================
echo   Ready. Launching RAG Assistant...
echo ========================================

:: Kill old instances - kill old server process
echo [*] cleaning old process...
:: 方法1: 按 PID 文件杀（最精准）
if exist "%~dp0server.pid" (
    set /p OLD_PID=<"%~dp0server.pid"
    taskkill /F /PID !OLD_PID! >nul 2>&1
    ping 127.0.0.1 -n 2 >nul
)
:: 方法2: 按端口杀（兜底）
powershell -NoProfile -Command "& {Get-NetTCPConnection -LocalPort 8765,8766 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }}" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start server
cd /d "%~dp0"
start /B "" python main.py --pidfile "%~dp0server.pid"

:: Wait for server to start（轮询端口，自适应等待）
echo Waiting for server...
echo   加载模型 + KB 索引探测中，请稍候...
:wait_loop
timeout /t 1 /nobreak >nul 2>&1
netstat -ano 2>nul | findstr ":8765 " | findstr "LISTENING" >nul
if errorlevel 1 goto wait_loop

:: Open browser
start http://localhost:8765

echo.
echo Server is running at: http://localhost:8765
echo Close this window to stop the server.
echo.
