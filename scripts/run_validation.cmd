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

echo [INFO] Running pytest...
uv run --with pytest pytest -q
if errorlevel 1 (
  echo [ERROR] Pytest execution failed.
  popd
  pause
  exit /b 1
)

echo [INFO] Running ruff lint check...
uv run --with ruff ruff check src tests --no-cache
if errorlevel 1 (
  echo [ERROR] Ruff lint check failed.
  popd
  pause
  exit /b 1
)

echo [INFO] All validation checks passed successfully!
popd
exit /b 0
