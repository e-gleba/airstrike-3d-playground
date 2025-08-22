@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo error: no executable specified
    echo usage: %~nx0 ^<executable^> [args...]
    set /p "dummy=press enter to exit..."
    exit /b 1
)

rem bulletproof timestamp - no wmic garbage
for /f "tokens=1-3 delims=/" %%a in ("%date%") do set "d=%%c%%a%%b"
for /f "tokens=1-3 delims=:" %%a in ("%time%") do set "t=%%a%%b%%c"
set "t=%t: =0%"

echo === steam proton debug session ===
echo timestamp: %date% %time%
echo executable: %~1
echo arguments: %*
echo working_directory: %cd%
echo user: %username%
echo === environment ===
set STEAM_COMPAT_DATA_PATH
set PROTON_VERSION  
set WINEPREFIX
echo === execution start ===

"%~1" %~2 %~3 %~4 %~5 %~6 %~7 %~8 %~9
set "exit_code=%errorlevel%"

echo === execution complete ===
echo exit_code: %exit_code%

if not %exit_code%==0 (
    echo === error analysis ===
    powershell -nop -ex bypass -c "try{[ComponentModel.Win32Exception]::new(%exit_code%).Message}catch{'error_lookup_failed'}" 2>nul
)

set /p "dummy=press enter to exit..."
exit /b %exit_code%
