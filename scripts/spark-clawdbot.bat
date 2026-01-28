@echo off
set "CMD=%SPARK_CLAWDBOT_CMD%"
if "%CMD%"=="" set "CMD=%CLAWDBOT_CMD%"
if "%CMD%"=="" set "CMD=clawdbot"
python -m spark.cli sync-context
%CMD% %*
