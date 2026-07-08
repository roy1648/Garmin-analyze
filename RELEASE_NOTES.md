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
- Packaging readiness documentation.

### Not included

- Garmin Connect API.
- Cloud sync.
- Login.
- Database.
- Charts.
- AI coaching.
- Medical interpretation.
- HR / Garmin zone inference.
- Planned workout matching.
- Standalone EXE.
- Installer.
- PyInstaller packaging.
- EXE packaging.

### Required validation before release

- Automated tests pass.
- Ruff passes.
- CLI smoke test passes.
- Windows UI smoke test passes.
- No private Garmin data committed.
