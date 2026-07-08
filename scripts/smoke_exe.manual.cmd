@echo off
setlocal enabledelayedexpansion

echo ===============================================================
echo [INFO] Starting Windows EXE Smoke Test...
echo ===============================================================

set CLI_EXE=dist\garmin-tcx-ai\garmin-tcx-ai.exe
set UI_EXE=dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe

:: 1. Verify CLI EXE exists
if not exist "%CLI_EXE%" (
    echo [ERROR] CLI EXE not found at: %CLI_EXE%
    echo [ERROR] Please run "scripts\build_exe.manual.cmd" first.
    exit /b 1
)

:: 2. Clean up previous smoke outputs
if exist data\processed\exe_cli_smoke rd /s /q data\processed\exe_cli_smoke

echo [INFO] Running CLI EXE bundle command on minimal_running.tcx...
"%CLI_EXE%" bundle ^
  --input tests\fixtures\minimal_running.tcx ^
  --output data\processed\exe_cli_smoke ^
  --gps-policy redact_start_end ^
  --timezone Asia/Taipei ^
  --write-coach-handoff

if %ERRORLEVEL% neq 0 (
    echo [ERROR] CLI EXE failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

:: 3. Verify output files exist
set SMOKE_FAILED=0

if not exist data\processed\exe_cli_smoke\session_bundle\session_bundle.json (
    echo [ERROR] Missing expected output: data\processed\exe_cli_smoke\session_bundle\session_bundle.json
    set SMOKE_FAILED=1
)
if not exist data\processed\exe_cli_smoke\session_bundle\session_bundle.md (
    echo [ERROR] Missing expected output: data\processed\exe_cli_smoke\session_bundle\session_bundle.md
    set SMOKE_FAILED=1
)
if not exist data\processed\exe_cli_smoke\session_bundle\coach_handoff.md (
    echo [ERROR] Missing expected output: data\processed\exe_cli_smoke\session_bundle\coach_handoff.md
    set SMOKE_FAILED=1
)

if "%SMOKE_FAILED%"=="1" (
    echo [ERROR] CLI EXE Smoke Test Failed: Output files are missing or incomplete.
    exit /b 1
)

echo [SUCCESS] CLI EXE Smoke Test Passed!
echo.
echo ===============================================================
echo [INFO] Verifying UI EXE...
echo ===============================================================

if not exist "%UI_EXE%" (
    echo [WARNING] UI EXE not found at: %UI_EXE%
    echo [WARNING] Please ensure both CLI and UI specs are built.
) else (
    echo [INFO] UI EXE found at: %UI_EXE%
    echo.
    echo MANUAL UI VERIFICATION INSTRUCTIONS:
    echo -----------------------------------------------------------
    echo 1. Start the Streamlit UI EXE by running:
    echo    %UI_EXE%
    echo.
    echo 2. Verify that:
    echo    - A command prompt window opens.
    echo    - The Streamlit local server starts and prints URLs.
    echo    - A browser window opens automatically or you can navigate to http://localhost:8501.
    echo.
    echo 3. In the Web UI:
    echo    - Click the native path picker button and select "tests\fixtures\minimal_running.tcx"
    echo    - Keep the default output directory or set a custom one.
    echo    - Click "Run Conversion".
    echo    - Verify the "Open Output Folder" action works.
    echo    - Check the rendered markdown outputs and try copy / manual-copy buttons.
    echo.
    echo 4. Close the command prompt window containing the running UI to stop the server.
    echo -----------------------------------------------------------
)
echo.
echo ===============================================================
