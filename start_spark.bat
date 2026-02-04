@echo off
REM Spark Intelligence - Windows Startup Script
REM Starts: sparkd (8787), bridge_worker, dashboard (8585), pulse (8765), meta-ralph (8586), watchdog

setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
cd /d %~dp0

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
