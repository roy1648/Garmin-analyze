# Windows Launcher Scripts

These scripts are convenience wrappers for Windows local usage.

## Scripts

### `run_ui.cmd`

Starts the Streamlit Local UI:

```cmd
scripts\run_ui.cmd
```

### `run_cli_smoke.cmd`

Runs a small CLI smoke test using `tests/fixtures/minimal_running.tcx`:

```cmd
scripts\run_cli_smoke.cmd
```

### `run_validation.cmd`

Runs dependency sync, pytest, and ruff:

```cmd
scripts\run_validation.cmd
```

### `build_exe.manual.cmd` / `smoke_exe.manual.cmd`

Build the Windows EXEs with PyInstaller, then smoke test them:

```cmd
scriptsuild_exe.manual.cmd
scripts\smoke_exe.manual.cmd
```

The smoke test checks the CLI EXE text outputs and legacy opt-in outputs,
then calls `smoke_ui_exe.ps1` to confirm the UI EXE starts and answers
HTTP 200. See `docs/09_windows_exe_packaging.md`.

### `smoke_ui_exe.ps1`

Starts the packaged UI EXE, waits for its listening port, requests the
page and stops the process:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_ui_exe.ps1
```

## Requirements

* Windows CMD.
* `uv` installed and available in PATH.
* Python is managed through `uv`; do not use system Python directly.

## Notes

* `run_ui.cmd`, `run_cli_smoke.cmd` and `run_validation.cmd` do not create an EXE.
* Only `build_exe.manual.cmd` packages the application; never commit `dist/` or `build/`.
* Generated smoke-test outputs are written under `data/processed/`, which should remain uncommitted.
