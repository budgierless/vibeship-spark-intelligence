@echo off
set "CMD=%SPARK_CURSOR_CMD%"
if "%CMD%"=="" set "CMD=%CURSOR_CMD%"
if "%CMD%"=="" set "CMD=cursor"
python -m spark.cli sync-context
%CMD% %*
