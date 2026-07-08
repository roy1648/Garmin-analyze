# Release Notes Draft

## Garmin TCX AI Local RC

### Included

- TCX bundle generation through CLI.
- Shared pipeline use case.
- Local Streamlit UI.
- Input path validation.
- GPS privacy policy selection.
- Coach handoff Markdown output.
- Session bundle JSON / Markdown output.
- Native local path picker.
- Output folder open action.
- Copy/manual-copy actions for generated outputs.
- Windows launcher scripts:
  - `scripts/run_ui.cmd`
  - `scripts/run_cli_smoke.cmd`
  - `scripts/run_validation.cmd`
- Local Garmin Connect TCX importer.
- Garmin Connect `import-garminconnect` CLI command.
- Local UI data source selection (Local TCX vs Garmin Connect download).
- Garmin Connect download mode in Local UI.
- Windows Credential Manager / keyring password storage for Garmin Connect UI.
- Windows EXE Packaging Kit (spec files and build/smoke/clean scripts).

### Not included

- Committed binary executables (`*.exe` or `dist/` folders in git).
- Installer.
- Onefile EXE (deferred).
- Official Garmin Developer Program API (uses local-only unofficial importer).
- Cloud sync.
- Real Garmin Connect login in automated CI/tests (requires local user manual operation).
- Database.
- Charts.
- AI coaching.
- Medical interpretation.
- HR / Garmin zone inference.
- Planned workout matching.
- Background sync / scheduler.

### Required validation before release

- Automated tests pass.
- Ruff passes.
- CLI smoke test passes.
- Windows UI smoke test passes.
- No private Garmin data committed.
