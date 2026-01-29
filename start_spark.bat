@echo off
REM Spark Intelligence - Windows Startup Script
REM Starts: sparkd (8787), bridge_worker, dashboard (8585)

setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
set SPARK_DIR=%~dp0
set SPARK_DATA=%USERPROFILE%\.spark
set PID_DIR=%SPARK_DATA%\pids
set LOG_DIR=%SPARK_DATA%\logs
set SPARK_LOG_DIR=%LOG_DIR%

REM Create directories
if not exist "%SPARK_DATA%" mkdir "%SPARK_DATA%"
if not exist "%PID_DIR%" mkdir "%PID_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo =============================================
echo   SPARK - Self-Evolving Intelligence Layer
echo =============================================
echo.

REM Start sparkd (main daemon - port 8787)
echo [SPARK] Starting sparkd on port 8787...
start /B "" python "%SPARK_DIR%sparkd.py"
timeout /t 1 /nobreak > nul

REM Start bridge_worker (syncs learnings)
echo [SPARK] Starting bridge_worker...
start /B "" python "%SPARK_DIR%bridge_worker.py" --interval 30
timeout /t 1 /nobreak > nul

REM Start dashboard (port 8585)
echo [SPARK] Starting dashboard on port 8585...
start /B "" python "%SPARK_DIR%dashboard.py"

REM Start watchdog (auto-restart + queue warnings)
if "%SPARK_NO_WATCHDOG%"=="" (
    echo [SPARK] Starting watchdog...
    start /B "" python "%SPARK_DIR%scripts\watchdog.py" --interval 60
)

echo.
echo [SPARK] All services starting...
timeout /t 2 /nobreak > nul

REM Health check
echo.
echo [SPARK] Checking health...
curl -s http://127.0.0.1:8787/health > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   sparkd:    http://127.0.0.1:8787/health [OK]
) else (
    echo   sparkd:    http://127.0.0.1:8787/health [Starting...]
)

echo   Dashboard: http://127.0.0.1:8585
echo.
echo [SPARK] Logs: %LOG_DIR%
echo.
echo Press any key to exit (services will continue running)...
pause > nul
