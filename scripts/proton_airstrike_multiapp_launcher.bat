@echo off
setlocal enabledelayedexpansion

echo [launch] proton multi-app launcher
echo [launch] starting tools...

start "" "Scylla_v0.9.8\Scylla_x86.exe"
call :check_start "scylla"

start "" "CheatEngine76.exe" 
call :check_start "cheat_engine"

start "" "release\x32\x32dbg.exe"
call :check_start "x32dbg"

echo [launch] starting target...
start "" "AirStrike3D II.exe" %*
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

