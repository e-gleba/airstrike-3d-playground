@echo off
setlocal enabledelayedexpansion

REM Add this .bat file as external game in Steam:
REM Steam -> Add a Game -> Add a Non-Steam Game -> Browse to this .bat file
REM Set launch options if needed and run through Proton

echo [launch] proton multi-app launcher
echo [launch] starting tools...

start "" "Scylla_v0.9.8\Scylla_x86.exe"
call :check_start "scylla"

start "" "CheatEngine76.exe" 
call :check_start "cheat_engine"

start "" "release\x32\x32dbg.exe"
call :check_start "x32dbg"

echo [launch] starting target...
start "" "as3d2.exe" %*
call :check_start "airstrike3d"

echo [launch] all processes launched successfully
pause >nul
exit /b 0

:check_start
if errorlevel 1 (
    echo [error] failed to start %~1 - exit code: %errorlevel%
    echo [error] possible causes: file not found, access denied, or invalid path
    pause
    exit /b %errorlevel%
)
echo [info] %~1 started successfully
goto :eof

