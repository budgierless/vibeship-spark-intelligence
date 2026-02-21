@echo off
echo.
echo   SPARK DEPTH TRAINING
echo   Autonomous Socratic reasoning gym
echo   ==========================================
echo.

REM Check if DEPTH server is running
curl -s http://localhost:5555/api/health >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!!] DEPTH server not running on :5555
    echo   Starting DEPTH server...
    if "%DEPTH_GAME_PATH%"=="" set "DEPTH_GAME_PATH=%~dp0..\vibeship-depth-game"
    start "DEPTH Server" /D "%DEPTH_GAME_PATH%" cmd /c "python server.py"
    echo   Waiting for server to start...
    ping -n 5 127.0.0.1 >nul
)

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!!] Ollama not running. Please start: ollama serve
    pause
    exit /b 1
)

echo   Prerequisites OK. Starting training...
echo.

cd /d "%~dp0"
python scripts/run_depth_training.py --cycles 5

echo.
echo   Training complete. Run 'python -m lib.depth_trainer --dashboard' for stats.
pause

