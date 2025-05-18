@echo off

SET "SCRIPT_DIR=%~dp0"
SET "PROJECT_ROOT=%SCRIPT_DIR%.."
FOR %%i IN ("%PROJECT_ROOT%") DO SET "PROJECT_ROOT=%%~fi"

echo [+] Project Root determined as: %PROJECT_ROOT%

CALL "%PROJECT_ROOT%\venv\Scripts\activate"
IF ERRORLEVEL 1 (
    echo [!] Failed to activate virtual environment. Make sure venv exists in %PROJECT_ROOT% and is set up.
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

pyinstaller --clean --onefile --noconsole ^
    --name "MediaCatalogBot" ^
    --icon="resources/ico.ico" ^
    --add-data "config_templates/config.py.default:." ^
    --add-data "VERSION:." ^
    --add-data "resources/ico.ico:." ^
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
IF EXIST "%PROJECT_ROOT%\Media Catalog Telegram Bot.spec" (
    echo [-] Deleting Media Catalog Telegram Bot.spec
    del "%PROJECT_ROOT%\Media Catalog Telegram Bot.spec"
)
IF EXIST "%PROJECT_ROOT%\build" (
    echo [-] Deleting build directory...
    rmdir /S /Q "%PROJECT_ROOT%\build"
)

echo [+] Cleanup complete.

:eof
echo [+] Build process finished.