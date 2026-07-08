@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."

pushd "%REPO_ROOT%" || (
  echo [ERROR] Failed to enter repository root.
  pause
  exit /b 1
)

uv --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] uv is not installed or not available in PATH.
  echo Please install uv first, then re-run this launcher.
  popd
  pause
  exit /b 1
)

echo [INFO] Syncing dependencies...
uv sync
if errorlevel 1 (
  echo [ERROR] uv sync failed.
  popd
  pause
  exit /b 1
)

echo [INFO] Running CLI smoke test...
uv run garmin-tcx-ai bundle ^
  --input tests/fixtures/minimal_running.tcx ^
  --output data/processed/launcher_cli_smoke ^
  --gps-policy redact_start_end ^
  --timezone Asia/Taipei ^
  --write-coach-handoff
if errorlevel 1 (
  echo [ERROR] CLI execution failed.
  popd
  pause
  exit /b 1
)

echo [INFO] Verifying output files...
set "OUTPUT_DIR=data\processed\launcher_cli_smoke\session_bundle"

if not exist "%OUTPUT_DIR%\session_bundle.json" (
  echo [ERROR] Missing expected output: %OUTPUT_DIR%\session_bundle.json
  popd
  pause
  exit /b 1
)

if not exist "%OUTPUT_DIR%\session_bundle.md" (
  echo [ERROR] Missing expected output: %OUTPUT_DIR%\session_bundle.md
  popd
  pause
  exit /b 1
)

if not exist "%OUTPUT_DIR%\coach_handoff.md" (
  echo [ERROR] Missing expected output: %OUTPUT_DIR%\coach_handoff.md
  popd
  pause
  exit /b 1
)

echo [INFO] CLI smoke test passed successfully!
popd
exit /b 0
