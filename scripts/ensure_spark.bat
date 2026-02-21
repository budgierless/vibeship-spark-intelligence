@echo off
REM Ensure Spark is running for the current project

setlocal
set PROJECT_DIR=%cd%
if "%SPARK_PULSE_DIR%"=="" (
    set "SPARK_PULSE_DIR=%~dp0..\..\vibeship-spark-pulse"
    if not exist "%SPARK_PULSE_DIR%\app.py" echo [warn] vibeship-spark-pulse not found. Set SPARK_PULSE_DIR to its location.
)
python -m spark.cli ensure --sync-context --project "%PROJECT_DIR%"
