# Windows Launcher and Packaging Readiness

## Purpose

This phase prepares the project for easier Windows local usage before attempting EXE packaging.

## Current delivery mode

Current recommended local usage:

```cmd
scripts\run_ui.cmd
```

Developer validation:

```cmd
scripts\run_validation.cmd
scripts\run_cli_smoke.cmd
```

## Why not EXE yet

This PR intentionally does not create an EXE because:

* Streamlit packaging has runtime complexity.
* Native file picker behavior should be manually validated first.
* UI startup, browser behavior, and output-folder actions should be stable before packaging.
* Packaging should not be mixed with release candidate documentation or launcher scripts.

## Packaging readiness checklist

Before EXE packaging spike:

* [ ] `scripts\run_ui.cmd` starts Streamlit UI on Windows.
* [ ] UI launches without `st.components.v1.html` warning.
* [ ] Native TCX file picker works.
* [ ] Native TCX folder picker works.
* [ ] Native output folder picker works.
* [ ] CLI smoke test passes.
* [ ] Validation script passes.
* [ ] No private data is committed.
* [ ] Known limitations are documented.
* [ ] Release candidate checklist is up to date.

## Candidate packaging strategies

### Option A: Keep launcher-based delivery

Pros:

* Lowest risk.
* Uses uv-managed environment.
* Easy to debug.
* No PyInstaller complexity.

Cons:

* Requires uv installed.
* Not a standalone app.

### Option B: Package CLI only

Pros:

* Lower risk than Streamlit UI packaging.
* Easier to test.
* Useful for automation.

Cons:

* Does not solve Local UI packaging.

### Option C: Package Streamlit UI launcher

Pros:

* Better user experience.
* Can be closer to double-click app behavior.

Cons:

* Higher risk.
* Needs runtime path handling.
* Needs Streamlit static asset handling.
* Browser/port behavior must be handled.
* May require one-dir distribution rather than single-file EXE.

## Recommended next step

The Windows EXE Packaging Kit has been established in Phase 25 (PR #25). 

To proceed with manual PyInstaller execution, testing, and troubleshooting, please refer to:
- [docs/09_windows_exe_packaging.md](file:///d:/01-Git%20code/10-garmin%20project/docs/09_windows_exe_packaging.md)
