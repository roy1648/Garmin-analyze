# Windows EXE Packaging

## Goal

This document describes how to manually build Windows EXE bundles for:
- CLI: `garmin-tcx-ai.exe`
- Local UI: `garmin-tcx-ai-ui.exe`

Currently, the EXE packaging target supports the `garminconnect` optional UI/CLI dependencies (including `curl_cffi` and `keyring`).

## Current strategy

- Use PyInstaller.
- Use `onedir` distribution (onefile is still deferred).
- Keep console enabled.
- Do not create installer yet (installer is deferred).
- Do not commit `dist/`, `build/`, `.exe`, or packaging logs.
- The build script (`scripts\build_exe.manual.cmd`) syncs dependencies using `uv sync --extra garminconnect` and packages with PyInstaller containing all optional features.

## Why human-run build

PyInstaller may generate large logs and environment-specific failures.
To reduce AI token usage:
- the human operator runs build scripts locally.
- logs are written to `.packaging-logs/`.
- only the last 80 lines or focused error snippets should be shared with AI.

## Build

```cmd
scripts\build_exe.manual.cmd
```

## Smoke test

```cmd
scripts\smoke_exe.manual.cmd
```

The smoke test validates basic CLI help commands (including `import-garminconnect --help`) and does NOT make real network requests to Garmin Connect.

## Clean

```cmd
scripts\clean_packaging_artifacts.cmd
```

## Expected outputs

```text
dist\garmin-tcx-ai\garmin-tcx-ai.exe
dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe
```

## What to report back to AI

If build succeeds:

* build script success line
* output folder listing
* smoke test result

If build fails:

* failed phase: CLI or UI
* log file path
* last 80 lines only
* first clear ERROR block if visible
* do not paste full log

## Manual Verification Safety Boundaries

* **No Automated Real Logins**: Real Garmin Connect logins and Windows Credential Manager keyring storage are **never** executed in automated smoke tests or CI.
* **Manual UI Integration Test**: Real login integration and keyring retrieval should be manually verified by the user locally:
  1. Launch the UI EXE `dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe`.
  2. Switch data source to "Garmin Connect 下載".
  3. Verify email/password/keyring UI elements are visible.
  4. Perform an optional real login/download check.
* **Onefile and Installer**: Standalone onefile packaging and installers remain deferred. Do not commit build results.
