# Release Notes

## v0.2.0 — AI text export and simpler UI

### Release metadata

- **Version**: v0.2.0
- **Python package version**: 0.2.0
- **Windows EXE FileVersion/ProductVersion**: 0.2.0

### Changed

- New default output: plain-text files for AI use.
  - `summary.txt`: period totals, Monday-to-Sunday weekly totals, daily
    totals and one line per run.
  - `runs/<date>_<time>_<km>km.txt`: one file per run with overview,
    per-lap table and adaptively sampled trackpoints (short laps stay
    dense so intervals survive; long laps are sparse).
  - `all_in_one.txt`: summary, then every run's overview and lap table,
    then an appendix with the sampled trackpoints, for one-shot
    upload/paste.
  - Weekly table has a 完整度 column marking partial weeks (based on the
    requested download range when available, else on the run dates).
  - Text outputs never contain GPS coordinates.
- Legacy `session_bundle.json` / `session_bundle.md` / `coach_handoff.md`
  are now opt-in (`--write-session-bundle`, `--write-coach-handoff`,
  or the UI "舊版輸出" checkboxes).
- New CLI options: `--trackpoint-density {compact,standard,detailed}`,
  `--no-ai-text`, `--write-session-bundle`.
- Streamlit UI redesigned as a three-step flow (source → output → run)
  with quick date-range buttons, previews, copy and download buttons.
- UI launcher picks a free port automatically (8501 when available),
  prints the URL and opens the browser once the server responds.
  `scripts\run_ui.cmd` now uses the same launcher.
- Packaged EXE stores downloads and outputs under
  `Documents\GarminTCX-AI\` so it works the same on any computer.

### Manual validation status

- Automated tests (`pytest`) verified and passing.
- EXE build/smoke must be run manually on Windows using
  `scripts\build_exe.manual.cmd` and `scripts\smoke_exe.manual.cmd`.

## v0.1.0 — Local Windows RC

### Release metadata

- **Version**: v0.1.0
- **Python package version**: 0.1.0
- **Windows EXE FileVersion/ProductVersion**: 0.1.0
- **Author**: Jia-Long Chen
- **GitHub**: roy1648
- **License**: MIT
- **Copyright**: Copyright (c) 2026 Jia-Long Chen

### Included

- CLI TCX bundle generation
- Streamlit Local UI
- Session bundle JSON / Markdown output
- Coach handoff Markdown output
- GPS privacy policy options
- Native local path picker
- Output folder open action
- Copy action for generated outputs
- Local Garmin Connect TCX importer
- import-garminconnect CLI command
- Local UI data source selection
- Garmin Connect download mode in Local UI
- Windows Credential Manager / keyring password storage
- Windows onedir EXE packaging
- Windows launcher scripts (`scripts\run_ui.cmd`, `scripts\run_cli_smoke.cmd`, `scripts\run_validation.cmd`)

### Manual validation status

- Automated tests (`pytest`) and linting (`ruff`) are verified and passing.
- EXE build/smoke not run by Agent; must be run manually on Windows using `scripts\build_exe.manual.cmd` and `scripts\smoke_exe.manual.cmd`.
- Real Garmin login and Windows Credential Manager keyring storage have been manually validated by the user in a local environment.

### Known limitations

- Real Garmin Connect login is manual local-only.
- Real Windows Credential Manager validation is manual local-only.
- Native file picker depends on local OS / tkinter availability; manual path input remains the fallback.
- Clipboard copy depends on browser-side copy permissions; manual copy is provided as a fallback.
- Primary expected operating environment is Windows local machine.

### Not included

- No official Garmin Developer Program API (uses local-only unofficial importer)
- No cloud sync
- No database
- No background scheduler
- No AI coaching
- No medical interpretation
- No HR zone / Garmin zone inference
- No planned workout matching
- No installer
- No onefile EXE

### Data safety notes

- Do not commit dist/
- Do not commit build/
- Do not commit .packaging-logs/
- Do not commit *.exe
- Do not commit *.zip release artifacts
- Do not commit raw TCX / FIT / GPX / KML
- Do not commit Garmin token / credential / .env / ~/.garminconnect

### Release artifacts

- **ZIP Name**: `garmin-tcx-ai-v0.1.0-windows-onedir.zip` (Do NOT commit to repository)
- **Included Folders / Files**:
  - `dist\garmin-tcx-ai\` (CLI executable folder)
  - `dist\garmin-tcx-ai-ui\` (UI executable folder)
  - `README.md`
  - `LICENSE`
  - `NOTICE.md`
  - `RELEASE_NOTES.md`
  - `docs\10_final_release_checklist.md`
- **Upload target**: Hand-upload the ZIP artifact manually to the GitHub Release.
