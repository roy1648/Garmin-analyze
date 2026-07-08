@echo off
setlocal enabledelayedexpansion

echo ===============================================================
echo [INFO] Cleaning packaging artifacts and smoke outputs...
echo ===============================================================

if exist build (
    echo [INFO] Removing "build" directory...
    rd /s /q build
)

if exist dist (
    echo [INFO] Removing "dist" directory...
    rd /s /q dist
)

if exist .packaging-logs (
    echo [INFO] Removing ".packaging-logs" directory...
    rd /s /q .packaging-logs
)

if exist data\processed\exe_cli_smoke (
    echo [INFO] Removing "data\processed\exe_cli_smoke" directory...
    rd /s /q data\processed\exe_cli_smoke
)

if exist data\processed\launcher_cli_smoke (
    echo [INFO] Removing "data\processed\launcher_cli_smoke" directory...
    rd /s /q data\processed\launcher_cli_smoke
)

echo.
echo [SUCCESS] Packaging artifacts and smoke outputs cleaned successfully!
echo ===============================================================
