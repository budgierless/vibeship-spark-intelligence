@echo off
REM Spark Intelligence - Stop all services

echo [SPARK] Stopping all Spark services...
cd /d %~dp0
python -m spark.cli down
echo [SPARK] Services stopped.
pause
