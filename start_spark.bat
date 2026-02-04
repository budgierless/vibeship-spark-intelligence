@echo off
REM Spark Intelligence - Windows Startup Script
REM Starts: Mind (8080), sparkd (8787), bridge_worker, dashboard (8585), pulse (8765), meta-ralph (8586), watchdog

setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
cd /d %~dp0

if "%SPARK_NO_MIND%"=="1" goto start_spark
set MIND_PORT=%SPARK_MIND_PORT%
if "%MIND_PORT%"=="" set MIND_PORT=8080
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_mind.ps1" -MindPort %MIND_PORT%

:start_spark
echo.
echo =============================================
echo   SPARK - Self-Evolving Intelligence Layer
echo =============================================
echo.

python -m spark.cli up
python -m spark.cli services

echo.
echo Press any key to exit (services will continue running)...
pause > nul
