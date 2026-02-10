@echo off
set "CMD=%SPARK_CODEX_CMD%"
if "%CMD%"=="" set "CMD=%CODEX_CMD%"
if "%CMD%"=="" set "CMD=codex"
python -m spark.cli sync-context
%CMD% %*
