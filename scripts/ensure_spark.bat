@echo off
REM Ensure Spark is running for the current project

setlocal
set PROJECT_DIR=%cd%
if "%SPARK_PULSE_DIR%"=="" (
    set "SPARK_PULSE_DIR=%~dp0..\..\vibeship-spark-pulse"
    if not exist "%SPARK_PULSE_DIR%\app.py" set "SPARK_PULSE_DIR=%USERPROFILE%\Desktop\vibeship-spark-pulse"
)
python -m spark.cli ensure --sync-context --project "%PROJECT_DIR%"
