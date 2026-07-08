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

## Requirements

* Windows CMD.
* `uv` installed and available in PATH.
* Python is managed through `uv`; do not use system Python directly.

## Notes

* These scripts do not create an EXE.
* These scripts do not package the application.
* Generated smoke-test outputs are written under `data/processed/`, which should remain uncommitted.
