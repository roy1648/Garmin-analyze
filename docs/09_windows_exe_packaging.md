# Windows EXE Packaging

## Goal

This document describes how to manually build Windows EXE bundles for:
- CLI: `garmin-tcx-ai.exe`
- Local UI: `garmin-tcx-ai-ui.exe`

## Current strategy

- Use PyInstaller.
- Use onedir first.
- Keep console enabled for first packaging spike.
- Do not create installer yet.
- Do not commit `dist/`, `build/`, `.exe`, or packaging logs.

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

## Known risks

* Streamlit packaging may require additional data files or hidden imports.
* UI EXE may need onedir distribution.
* Onefile is intentionally deferred.
* Browser/port behavior must be manually verified.
* Native file picker must be manually verified in packaged UI.
