@echo off
setlocal enabledelayedexpansion

echo ===============================================================
echo [INFO] Starting Windows EXE Packaging Process...
echo ===============================================================

:: Sync dependencies first
echo [INFO] Running uv sync...
call uv sync --extra garminconnect
if %ERRORLEVEL% neq 0 (
    echo [ERROR] uv sync failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

:: Create log folder
if not exist .packaging-logs mkdir .packaging-logs

:: Generate timestamp using powershell to avoid regional format discrepancies
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set TIMESTAMP=%%i

set CLI_LOG=.packaging-logs\pyinstaller_cli_%TIMESTAMP%.log
set UI_LOG=.packaging-logs\pyinstaller_ui_%TIMESTAMP%.log

echo [INFO] Building CLI EXE with garminconnect optional dependency...
echo [INFO] Logging to: %CLI_LOG%
call uv run --extra garminconnect --with pyinstaller pyinstaller --clean --noconfirm packaging/garmin-tcx-ai-cli.spec > "%CLI_LOG%" 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CLI Build Failed!
    echo [ERROR] Log file path: %CLI_LOG%
    echo -------------------- LAST 80 LINES OF LOG --------------------
    powershell -NoProfile -Command "Get-Content -Tail 80 '%CLI_LOG%'"
    echo ---------------------------------------------------------------
    exit /b 1
)
echo [INFO] CLI Build Succeeded!

echo [INFO] Building Streamlit UI EXE with garminconnect optional dependency...
echo [INFO] Logging to: %UI_LOG%
call uv run --extra garminconnect --with pyinstaller pyinstaller --clean --noconfirm packaging/garmin-tcx-ai-ui.spec > "%UI_LOG%" 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] UI Build Failed!
    echo [ERROR] Log file path: %UI_LOG%
    echo -------------------- LAST 80 LINES OF LOG --------------------
    powershell -NoProfile -Command "Get-Content -Tail 80 '%UI_LOG%'"
    echo ---------------------------------------------------------------
    exit /b 1
)
echo [INFO] UI Build Succeeded!

echo ===============================================================
echo [SUCCESS] Windows EXE Packaging Kit executed successfully!
echo ===============================================================
echo CLI EXE Folder: dist\garmin-tcx-ai\
echo UI EXE Folder:  dist\garmin-tcx-ai-ui\
echo.
echo IMPORTANT REMINDER:
echo Do not commit the following directories/files to git:
echo - dist/
echo - build/
echo - .packaging-logs/
echo - Any *.exe files
echo ===============================================================
