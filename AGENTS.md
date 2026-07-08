# AGENTS.md

## Project role

This is a personal Garmin Connect data ETL and analysis project.
The goal is to import, normalize, validate, and analyze Garmin activity
and health data for personal training review.

If behavior or data contracts are unclear, read `docs/` before editing.

## Engineering rules

- Use Python 3.12+.
- Follow PEP8.
- Use type hints for all public functions.
- Add English docstrings to all public functions.
- Keep each line under 79 characters where practical.
- Prefer small functions with clear input/output boundaries.
- Do not add production dependencies without explaining why.
- Do not store credentials, tokens, or raw personal data in Git.

## Testing rules

- Use pytest.
- Add or update tests for every behavior change.
- Network calls must be isolated behind interfaces.
- Unit tests must not call Garmin Connect directly.
- Use committed minimal sanitized fixtures under `tests/fixtures/`.
- Keep optional local samples under `data/samples/`, ignored by Git.
- Tests must not depend on private local samples.

## Data safety rules

- Never print Garmin passwords, tokens, or private raw data.
- Never commit files under `data/raw/` or `data/processed/`.
- Use `.env` only for local development and keep it ignored by Git.
- Prefer token/cache storage outside the repository.
- Treat GPS coordinates and health metrics as sensitive data.
- Never modify raw TCX input files.

## Scope boundaries

- MVP focuses on manually exported Garmin Connect Running TCX files.
- Do not add Web UI, database storage, Garmin API login, or cloud sync
  unless the user explicitly changes scope.
  - Approved Exception: Local-only Streamlit UI is allowed as a post-MVP usability layer.
  - Cloud dashboard, database, Garmin API login/sync, AI API upload, and AI coaching platform remain out of scope.
- GarminDB and python-garminconnect may be discussed in docs or roadmap,
  but must not be added as dependencies during MVP work.
- Do not build a full AI coaching platform in MVP.

## Done definition

A task is done only when:

- Relevant tests pass.
- Ruff or equivalent lint passes when configured.
- Documentation-only changes do not require test implementation.
- The diff is small enough to review.
- README or docs are updated if behavior changed.

## PR Operating Rules

Every PR must follow these guardrails to prevent scope creep:

### 1. One PR = One Objective

- Each PR focuses on a single, cohesive objective (e.g., "Implement TCX parser" or "Add JSON exporter").
- Do not combine parser work, exporter work, privacy logic, summary building, CLI, and batch processing in a single PR.
- If a PR becomes too large, split it into smaller, sequential PRs.

### 2. PR Template Requirements

Every PR must include:

**a) Objective**  
Clear one-sentence description of what this PR accomplishes.

**b) Allowed Files**  
Explicit list of which files this PR may modify (e.g., `src/garmin_tcx_ai/parser.py`, `tests/test_parser.py`).

**c) Forbidden Files**  
Explicit list of files this PR must NOT touch (e.g., `pyproject.toml`, `src/garmin_tcx_ai/cli.py`, `docs/04_architecture.md`).

**d) Non-goals**  
Explicit list of features explicitly NOT included in this PR (e.g., "does not handle Cycling activities", "does not implement batch mode").

**e) Verification Commands**  
Bash/PowerShell commands to verify the PR works locally (e.g., `pytest tests/test_parser.py`, `python scripts/convert_tcx.py --input tests/fixtures/minimal_running.tcx --output-dir /tmp/test`).

### 3. Scope Enforcement

- Do not implement roadmap items (GarminDB, python-garminconnect, Web UI, database, Garmin API, AI API upload) unless explicitly requested by the user in the task brief.
- If documentation and implementation status conflict, report the conflict in the PR description instead of expanding scope to "make them match."
- Do not add dependencies without explaining why in the PR description.
- Do not add CLI flags, config files, or feature gates beyond the original specification.

### 4. Data Safety & Security

- Never commit raw TCX files, `.env`, credentials, or personal raw data.
- Never print passwords, tokens, or private raw data in logs or tests.
- Treat GPS coordinates and health metrics as sensitive.
- Follow `docs/06_mvp_freeze.md` non-goals strictly.

### Example PR Description

```
## Objective
Implement TCX parser to extract activity, lap, and trackpoint data from Running activities.

## Allowed Files
- src/garmin_tcx_ai/parser.py
- tests/test_parser.py
- tests/fixtures/minimal_running.tcx (reference only)

## Forbidden Files
- pyproject.toml
- src/garmin_tcx_ai/exporters.py
- src/garmin_tcx_ai/summary.py
- docs/04_architecture.md

## Non-goals
- Does not normalize or validate data (that is normalizer's job).
- Does not apply privacy policies.
- Does not export to JSON, CSV, or Markdown.
- Does not handle non-Running activities.
- Does not cache or store results.

## Verification
python -m pytest tests/test_parser.py -v
```
