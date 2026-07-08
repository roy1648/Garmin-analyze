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

## Explicit Non-goals

- Garmin Connect API integration.
- Cloud sync.
- Database storage.
- User login.
- Charts / visualization.
- AI coaching.
- Medical interpretation.
- HR zone inference.
- Garmin zone inference.
- Planned workout matching.
- 課表角色推論.
- EXE packaging.
- File upload / drag-and-drop.

## Automated validation

List commands:

```powershell
uv sync
uv run python -m pytest -q
uv run python -m ruff check src tests --no-cache
```

For each command, include a result table:

| Check           | Command                                            | Result                    | Notes |
| --------------- | -------------------------------------------------- | ------------------------- | ----- |
| Dependency sync | `uv sync`                                          | Passed                    | Dependencies resolved and synced. |
| Test suite      | `uv run python -m pytest -q`                       | Passed                    | 175 passed in 1.52s. (Run dynamically as `uv run --with pytest pytest -q` due to pytest not in main dependency group) |
| Lint            | `uv run python -m ruff check src tests --no-cache` | Passed                    | All checks passed. (Run dynamically as `uv run --with ruff ruff check src tests --no-cache` due to ruff not in main dependency group) |

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

Current decision: Pending manual Windows smoke test.

A release may proceed only if:
- Automated tests pass.
- Ruff passes.
- CLI smoke test passes.
- Streamlit UI launches locally.
- Windows manual UI smoke test passes.
- No private Garmin data is committed.
- Known limitations are documented.
