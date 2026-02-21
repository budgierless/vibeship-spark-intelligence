@echo off
setlocal
cd /d "%~dp0.."
python -m spark.cli %*
exit /b %errorlevel%
