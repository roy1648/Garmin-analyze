# CLAUDE.md - Project Configuration

**Auto-loaded from AGENTS.md in the project root.**

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
