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

echo [INFO] Starting Garmin TCX AI Local UI...
uv run streamlit run src/garmin_tcx_ai/ui_streamlit.py
set "EXIT_CODE=%ERRORLEVEL%"

popd

if not "%EXIT_CODE%"=="0" (
  echo [ERROR] Streamlit exited with code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

exit /b 0
