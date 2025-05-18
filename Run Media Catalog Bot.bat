@echo off

SET "SCRIPT_DIR=%~dp0"

SET "PS_SCRIPT_PATH=%SCRIPT_DIR%src\scripts\run_mediacatalog.ps1"

IF NOT EXIST "%PS_SCRIPT_PATH%" (
    echo ERROR: PowerShell script not found at "%PS_SCRIPT_PATH%"
    echo Please ensure 'run_mediacatalog.ps1' is in the 'src\scripts' directory.
    pause
    exit /b 1
)

echo Starting Media Catalog Bot (background process)...

start "MediaCatalogBot PowerShell Launcher" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT_PATH%"

exit /b 0