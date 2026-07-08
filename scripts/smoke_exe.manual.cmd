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

:: 1b. Check CLI help commands (which must not trigger logins or request credentials)
echo [INFO] Verifying CLI EXE --help...
"%CLI_EXE%" --help > nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CLI EXE --help failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)
echo [INFO] CLI EXE --help passed.

echo [INFO] Verifying CLI EXE import-garminconnect --help...
"%CLI_EXE%" import-garminconnect --help > nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CLI EXE import-garminconnect --help failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)
echo [INFO] CLI EXE import-garminconnect --help passed.

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
    echo    - Verify that "資料來源" (Data Source Selection) appears at the top.
    echo    - Verify that you can switch between "本機 TCX 檔案 / 資料夾" and "Garmin Connect 下載".
    echo    - Switch to "Garmin Connect 下載" and verify you can see the following fields:
    echo      * Email
    echo      * Password (密碼)
    echo      * Date Range (活動下載日期範圍)
    echo      * Activity Type (下載活動類型)
    echo      * Download Folder (下載暫存路徑)
    echo      * Optional: "將密碼儲存到 Windows Credential Manager" checkbox
    echo    - Switch back to "本機 TCX 檔案 / 資料夾".
    echo    - Click the native path picker button and select "tests\fixtures\minimal_running.tcx"
    echo    - Keep the default output directory or set a custom one.
    echo    - Click "Run Conversion" (開始轉換).
    echo    - Verify the "Open Output Folder" (打開輸出資料夾) action works.
    echo    - Check the rendered markdown outputs and try copy / manual-copy buttons.
    echo.
    echo 4. Optional Manual Garmin Connect Integration Verification:
    echo    - Switch to "Garmin Connect 下載" mode.
    echo    - Enter your real Garmin Email and Password.
    echo    - Select a short date range (e.g. last 7 days).
    echo    - Check "將密碼儲存到 Windows Credential Manager".
    echo    - Click "Download and Convert" (開始下載與轉換) and verify it succeeds.
    echo    - Close and restart the UI EXE, verify you can use the stored password by
    echo      selecting "使用已儲存密碼".
    echo.
    echo 5. Close the command prompt window containing the running UI to stop the server.
    echo -----------------------------------------------------------
)
echo.
echo ===============================================================
