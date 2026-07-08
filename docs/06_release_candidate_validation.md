# Release Candidate Validation

## Scope

This release candidate covers:
- CLI TCX bundle generation.
- Shared `pipeline.run_bundle()` use case.
- Local Streamlit UI.
- Local-only file processing.
- Session bundle JSON / Markdown output.
- Coach handoff Markdown output.
- Privacy GPS policy options.
- Native local path picker.
- Output folder open action.
- Copy/manual-copy actions for generated output files.
- Garmin Connect CLI importer.
- UI data source selection (Local TCX vs Garmin Connect download).
- Garmin Connect UI mode with download functionality.
- Keyring / Windows Credential Manager integration for credential storage.
- Windows onedir EXE packaging (both CLI and UI).

## Explicit Non-goals

- Official Garmin Developer Program API (local-only unofficial importer is supported).
- Cloud sync.
- Database storage.
- Real Garmin Connect login/authentication in CI (local manual login only).
- Charts / visualization.
- AI coaching.
- Medical interpretation.
- HR zone inference.
- Garmin zone inference.
- Planned workout matching.
- 課表角色推論.
- Standalone onefile EXE (onedir is supported).
- Desktop Installer.
- File upload / drag-and-drop.

## Automated and Manual Validation

Validation commands:

```powershell
# Sync project dependencies (including optional Garmin Connect features)
uv sync --extra garminconnect

# Run unit and integration tests
uv run --with pytest pytest -q

# Run static analysis
uv run --with ruff ruff check src tests --no-cache

# Build Windows EXE packages (manual build script)
scripts\build_exe.manual.cmd

# Execute smoke test script for packaged EXEs
scripts\smoke_exe.manual.cmd
```

For each check, here is the validation result:

| Check           | Command                                            | Result                    | Notes |
| --------------- | -------------------------------------------------- | ------------------------- | ----- |
| Dependency sync | `uv sync --extra garminconnect`                    | Passed                    | Dependencies resolved and synced (including `garminconnect`, `curl_cffi`, `keyring`). |
| Test suite      | `uv run --with pytest pytest -q`                   | Passed                    | Passed (based on latest CI / local results). |
| Lint            | `uv run --with ruff ruff check src tests --no-cache` | Passed                    | All checks passed. |
| Manual build    | `scripts\build_exe.manual.cmd`                     | Verified                  | Executed locally to produce CLI/UI onedir EXE packages. |
| Smoke test      | `scripts\smoke_exe.manual.cmd`                     | Verified                  | CLI exit codes and fixture-based bundle operations pass. |

## CLI smoke test

Include command template:

```powershell
uv run garmin-tcx-ai bundle `
  --input tests/fixtures/minimal_running.tcx `
  --output data/processed/rc_cli_smoke `
  --gps-policy redact_start_end `
  --timezone Asia/Taipei `
  --write-coach-handoff
```

Expected outputs in `data/processed/rc_cli_smoke/session_bundle/`:
* `session_bundle.json`
* `session_bundle.md`
* `coach_handoff.md`

Actual CLI smoke test run:
- Executed on Windows local shell.
- Command completed successfully with output: `Successfully processed 1 activities. Output folder: D:\01-Git code\10-garmin project\data\processed\rc_cli_smoke`
- Checked directory `data/processed/rc_cli_smoke/session_bundle` and confirmed all three files are correctly generated.

## UI smoke test

Include command:

```powershell
uv run streamlit run src/garmin_tcx_ai/ui_streamlit.py
```

Manual checklist:
- [x] UI launches without `st.components.v1.html` deprecation warning. (Verified: Streamlit server starts up successfully on `http://localhost:8501`, no deprecation warning logs printed.)
- [ ] Manual input path works.
- [ ] 「選擇 TCX 檔案」 works on Windows.
- [ ] 「選擇 TCX 資料夾」 works on Windows.
- [ ] 「選擇輸出資料夾」 works on Windows.
- [ ] `tests/fixtures/minimal_running.tcx` can be processed.
- [ ] Output folder path is displayed.
- [ ] 「打開輸出資料夾」 works or fails gracefully.
- [ ] `session_bundle.json` preview works.
- [ ] `session_bundle.md` preview works.
- [ ] `coach_handoff.md` preview works.
- [ ] Copy/manual-copy works for all three generated files.
- [ ] GPS policy `keep` warning appears when selected.
- [ ] No private Garmin data is committed.

## Windows launcher validation

Commands:

```cmd
scripts\run_validation.cmd
scripts\run_cli_smoke.cmd
scripts\run_ui.cmd
```

Checklist:

* [ ] `scripts\run_validation.cmd` passes.
* [ ] `scripts\run_cli_smoke.cmd` produces expected output files.
* [ ] `scripts\run_ui.cmd` starts Streamlit UI.
* [ ] UI still launches without deprecated Streamlit component warning.
* [ ] No generated files are committed.

## Release Candidate Decision

Current decision: Final RC pending only if build/smoke not yet recorded.

### Manual UI EXE Smoke Validation (Verified locally by user)
- [x] UI EXE starts up successfully and console opens.
- [x] "資料來源" (Data Source Selection) switch displays at the top.
- [x] Switching between Local TCX and Garmin Connect download modes functions.
- [x] In Garmin Connect mode, Email/Password/keyring checkbox fields display correctly.
- [x] Native local path pickers function within the packaged UI EXE.
- [x] Session bundle generation executes successfully.
- [x] Windows Credential Manager integration is verified locally.

A release may proceed only if:
- Automated tests pass.
- Ruff passes.
- Packaged CLI EXE and UI EXE build and smoke tests pass.
- Packaged UI EXE has been manually verified locally.
- No private Garmin data is committed.
- Known limitations are documented.
