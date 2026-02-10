@echo off
REM Claude CLI wrapper for Python subprocess
REM Usage: claude_call.cmd <prompt_file> <response_file> [system_prompt_file]
setlocal enabledelayedexpansion

set "PFILE=%~1"
set "RFILE=%~2"
set "SFILE=%~3"

REM Read entire prompt from file
set "PROMPT="
for /f "usebackq delims=" %%a in ("%PFILE%") do (
    if defined PROMPT (
        set "PROMPT=!PROMPT! %%a"
    ) else (
        set "PROMPT=%%a"
    )
)

if defined SFILE if exist "%SFILE%" (
    set "SYS="
    for /f "usebackq delims=" %%a in ("%SFILE%") do (
        if defined SYS (
            set "SYS=!SYS! %%a"
        ) else (
            set "SYS=%%a"
        )
    )
    claude -p --output-format text --append-system-prompt "!SYS!" "!PROMPT!" > "%RFILE%" 2>nul
) else (
    claude -p --output-format text "!PROMPT!" > "%RFILE%" 2>nul
)
