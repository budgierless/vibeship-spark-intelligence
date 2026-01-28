@echo off
set "CMD=%SPARK_WINDSURF_CMD%"
if "%CMD%"=="" set "CMD=%WINDSURF_CMD%"
if "%CMD%"=="" set "CMD=windsurf"
python -m spark.cli sync-context
%CMD% %*
