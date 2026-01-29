@echo off
REM Spark Intelligence - Stop all services

echo [SPARK] Stopping all Spark services...

REM Kill Python processes running Spark components
tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr /i "sparkd" > nul
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "python.exe"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /i "sparkd.py bridge_worker.py dashboard.py watchdog.py" > nul && (
        taskkill /PID %%a /F > nul 2>&1
    )
)

REM Alternative: kill by port
echo [SPARK] Freeing ports 8787 and 8585...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8787') do taskkill /PID %%a /F > nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8585') do taskkill /PID %%a /F > nul 2>&1

echo [SPARK] Services stopped.
pause
