@echo off
set "CMD=%SPARK_CLAUDE_CMD%"
if "%CMD%"=="" set "CMD=%CLAUDE_CMD%"
if "%CMD%"=="" set "CMD=claude"
python -m spark.cli sync-context
%CMD% %*
