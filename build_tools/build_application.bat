@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

SET "SCRIPT_DIR=%~dp0"
SET "PROJECT_ROOT=%SCRIPT_DIR%.."
FOR %%i IN ("%PROJECT_ROOT%") DO SET "PROJECT_ROOT=%%~fi"

echo [+] Project Root determined as: %PROJECT_ROOT%

IF NOT EXIST "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found at "%PROJECT_ROOT%\venv\".
    echo [!] Please create and activate it first.
    goto :eof
)

echo [+] Activating virtual environment...
CALL "%PROJECT_ROOT%\venv\Scripts\activate.bat"
IF ERRORLEVEL 1 (
    echo [!] Failed to activate virtual environment.
    goto :eof
)

echo [+] Preparing version information...
python "%SCRIPT_DIR%build_set_version_info.py"
IF ERRORLEVEL 1 (
    echo [!] Error preparing build_version_details.txt. Aborting.
    goto :eof
)

echo [+] Running PyInstaller...
pushd "%PROJECT_ROOT%"

SET "OUTPUT_NAME=MediaCatalogBot"

pyinstaller --clean --onefile --noconsole ^
    --name "%OUTPUT_NAME%" ^
    --icon="resources/ico.ico" ^
    --add-data "config_templates/config.py.default:config_templates" ^
    --add-data "VERSION:." ^
    --add-data "resources/ico.ico:resources" ^
    --version-file "build_version_details.txt" ^
    --distpath "bin" ^
    MediaCatalog.py

IF ERRORLEVEL 1 (
    echo [!] PyInstaller failed.
    popd
    goto cleanup
) ELSE (
    echo [+] PyInstaller completed successfully. Output in %PROJECT_ROOT%\bin\
)
popd

:cleanup
echo [+] Cleaning up build files (relative to project root)...
IF EXIST "%PROJECT_ROOT%\build_version_details.txt" (
    echo [-] Deleting build_version_details.txt
    del "%PROJECT_ROOT%\build_version_details.txt"
)
IF EXIST "%PROJECT_ROOT%\%OUTPUT_NAME%.spec" (
    echo [-] Deleting %OUTPUT_NAME%.spec
    del "%PROJECT_ROOT%\%OUTPUT_NAME%.spec"
)
IF EXIST "%PROJECT_ROOT%\build" (
    echo [-] Deleting build directory...
    rmdir /S /Q "%PROJECT_ROOT%\build"
)

echo [+] Cleanup complete.

:eof
echo [+] Build process finished.
ENDLOCAL