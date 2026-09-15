@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ===============================================================
echo [INFO] Starting Windows EXE Smoke Test...
echo ===============================================================

set CLI_EXE=dist\garmin-tcx-ai\garmin-tcx-ai.exe
set UI_EXE=dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe
set SMOKE_OUT=data\processed\exe_cli_smoke
set LEGACY_OUT=data\processed\exe_cli_smoke_legacy
set SMOKE_FAILED=0

:: 1. Verify both EXEs exist
if not exist "%CLI_EXE%" (
    echo [ERROR] CLI EXE not found at: %CLI_EXE%
    echo [ERROR] Please run "scripts\build_exe.manual.cmd" first.
    exit /b 1
)
if not exist "%UI_EXE%" (
    echo [ERROR] UI EXE not found at: %UI_EXE%
    echo [ERROR] Please run "scripts\build_exe.manual.cmd" first.
    exit /b 1
)

:: 2. CLI help commands (must not trigger logins or request credentials)
echo [INFO] Verifying CLI EXE --help...
"%CLI_EXE%" --help > nul
if errorlevel 1 (
    echo [ERROR] CLI EXE --help failed.
    exit /b 1
)
echo [INFO] CLI EXE --help passed.

echo [INFO] Verifying CLI EXE import-garminconnect --help...
"%CLI_EXE%" import-garminconnect --help | findstr /C:"--trackpoint-density" > nul
if errorlevel 1 (
    echo [ERROR] import-garminconnect --help failed or lacks --trackpoint-density.
    echo [ERROR] The EXE may be built from an outdated source tree.
    exit /b 1
)
echo [INFO] CLI EXE import-garminconnect --help passed.

:: 3. Default run: AI text outputs only
if exist "%SMOKE_OUT%" rd /s /q "%SMOKE_OUT%"

echo [INFO] Running CLI EXE bundle on tests\fixtures (default AI text output)...
"%CLI_EXE%" bundle --input tests\fixtures --output "%SMOKE_OUT%" --timezone Asia/Taipei
if errorlevel 1 (
    echo [ERROR] CLI EXE bundle failed.
    exit /b 1
)

for %%F in (summary.txt all_in_one.txt) do (
    if not exist "%SMOKE_OUT%\%%F" (
        echo [ERROR] Missing expected output: %SMOKE_OUT%\%%F
        set SMOKE_FAILED=1
    )
)

set RUN_COUNT=0
if exist "%SMOKE_OUT%\runs" (
    for %%R in ("%SMOKE_OUT%\runs\*.txt") do set /a RUN_COUNT+=1
)
if !RUN_COUNT! LSS 1 (
    echo [ERROR] No per-run text files found in %SMOKE_OUT%\runs
    set SMOKE_FAILED=1
) else (
    echo [INFO] Per-run text files: !RUN_COUNT!
)

if exist "%SMOKE_OUT%\session_bundle" (
    echo [ERROR] Legacy session_bundle was written without being requested.
    set SMOKE_FAILED=1
)

:: 4. Legacy opt-in run: coach handoff implies the session bundle
if exist "%LEGACY_OUT%" rd /s /q "%LEGACY_OUT%"

echo [INFO] Running CLI EXE bundle with --write-coach-handoff (legacy opt-in)...
"%CLI_EXE%" bundle --input tests\fixtures\minimal_running.tcx --output "%LEGACY_OUT%" --write-coach-handoff > nul
if errorlevel 1 (
    echo [ERROR] CLI EXE legacy bundle failed.
    exit /b 1
)

for %%F in (session_bundle.json session_bundle.md coach_handoff.md) do (
    if not exist "%LEGACY_OUT%\session_bundle\%%F" (
        echo [ERROR] Missing expected legacy output: %LEGACY_OUT%\session_bundle\%%F
        set SMOKE_FAILED=1
    )
)

if "!SMOKE_FAILED!"=="1" (
    echo [ERROR] CLI EXE Smoke Test Failed: Output files are missing or unexpected.
    exit /b 1
)
echo [SUCCESS] CLI EXE Smoke Test Passed.
echo.

:: 5. UI EXE: start, wait for its listening port, request the page, stop.
::    The launcher picks a free port and opens the default browser; a
::    browser tab may appear during this step.
echo ===============================================================
echo [INFO] Verifying UI EXE starts and serves the page...
echo ===============================================================

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_ui_exe.ps1 -Exe "%UI_EXE%"
if errorlevel 1 (
    echo [ERROR] UI EXE Smoke Test Failed.
    exit /b 1
)
echo [SUCCESS] UI EXE Smoke Test Passed.
echo.

echo ===============================================================
echo MANUAL UI VERIFICATION (recommended before a release)
echo ---------------------------------------------------------------
echo 1. Start %UI_EXE%
echo    - A console window prints "[INFO] Garmin TCX AI UI: http://localhost:PORT".
echo    - The browser opens that URL automatically.
echo    - Start a second copy: it must pick a different port, not fail.
echo.
echo 2. Local mode:
echo    - Choose "本機 TCX 檔案 / 資料夾" and select tests\fixtures.
echo    - Keep the default output folder (Documents\GarminTCX-AI\processed\...).
echo    - Click "開始產生 AI 文字檔".
echo    - Verify the result shows summary.txt / runs / all_in_one.txt tabs.
echo    - Verify the weekly table has the 完整度 column.
echo    - Verify all_in_one.txt ends with the 附錄：軌跡取樣 section.
echo    - Try the copy and download buttons and "打開輸出資料夾".
echo.
echo 3. Garmin Connect mode (optional, real account):
echo    - Choose "Garmin Connect 下載", enter email and password.
echo    - Use a quick range button, e.g. 最近 14 天.
echo    - Tick the Windows Credential Manager checkbox and run.
echo    - Verify partial weeks are labelled against the chosen range.
echo    - Restart the EXE and verify the stored password is picked up.
echo.
echo 4. Close the console window to stop the server.
echo ===============================================================
exit /b 0
