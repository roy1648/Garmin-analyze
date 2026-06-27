# MVP Freeze Definition

**Date:** 2026-06-27  
**Status:** Locked for implementation  
**Next review:** After MVP completion or explicit scope change request

## MVP Done Definition

A task is complete and ready to merge only when:

1. **All tests pass** — relevant pytest tests must pass locally and in CI.
2. **Type hints and docstrings present** — all public functions have type hints and English docstrings.
3. **Code style validated** — Ruff or equivalent linting passes.
4. **Data contract compliance** — output files match schemas in `docs/02_data_contract.md`.
5. **Documentation updated** — if behavior changed, docs/README reflect it.
6. **Diff is reviewable** — single PR focused on one objective (see PR operating rules below).
7. **No credentials or raw data committed** — `.env`, `data/raw/`, `data/processed/` remain clean.

Documentation-only changes (e.g., docs updates without code changes) do not require test implementation.

## MVP Product Done Definition

MVP is **complete and shipped** only when all the following conditions are met:

### Input & Conversion

- ✅ A single sanitized Running TCX fixture (from `tests/fixtures/`) can be converted successfully.
- ✅ A single manually exported Running TCX file from Garmin Connect can be converted successfully.
- ✅ A folder containing one or more TCX files can be processed in batch mode without stopping on the first error.

### Output Files

Each valid Running TCX produces all four output files:

- ✅ `activity.json` — complete activity record with source, privacy, activity, laps, trackpoints, and warnings
- ✅ `trackpoints.csv` — UTF-8 CSV with all trackpoint data and required headers
- ✅ `ai_summary.json` — structured summary with activity_summary, key_metrics, lap_summary, trend_summary, privacy, data_quality, ai_context
- ✅ `ai_summary.md` — human-readable Markdown summary suitable for AI analysis

### Privacy & Data Handling

- ✅ GPS privacy policy (`gps_policy`) supports all three modes:
  - `keep` — all latitude/longitude preserved
  - `remove` — all latitude/longitude removed or null
  - `redact_start_end` — first 300m and last 300m (or 10% if insufficient distance) obscured
- ✅ Missing standard values follow the data contract:
  - JSON outputs use `null` for missing fields
  - CSV outputs use blank cells for missing values
  - AI summary mentions missing data only when it affects interpretation
- ✅ Raw TCX input files are **never** modified by the conversion process

### Warnings & Error Handling

- ✅ Warning records follow the complete schema:
  - `code` (e.g., "missing_optional_field", "unsupported_activity")
  - `severity` ("info", "warning", or "error")
  - `field` (specific field name or `null` if file-level)
  - `message` (readable explanation)
  - `source_file` (filename without full path)
- ✅ Unsupported non-Running activities are **not** silently treated as Running — they produce a readable warning and are skipped.
- ✅ Invalid XML produces a readable, actionable error message.
- ✅ Unsupported file types and missing input files produce clear error messages before conversion starts.

### Documentation

- ✅ README documents:
  - **Setup** — Python version, dependency installation, fixture verification
  - **Single-file usage** — example: `python scripts/convert_tcx.py --input /path/to/activity.tcx --output-dir /path/to/output`
  - **Folder/batch usage** — example: `python scripts/convert_tcx.py --input /path/to/folder --output-dir /path/to/output`
  - **GPS privacy options** — explanation of `--gps-policy keep|remove|redact_start_end`
  - **Generated output files** — what each of the four output files contains
  - **Known limitations** — Running activities only, manually exported TCX, no API/database integration
  - **Privacy warning** — GPS coordinates and heart rate are sensitive; advise user to review outputs before sharing with AI services

---

## MVP Non-goals

The following are explicitly **out of scope** for MVP and must not be implemented:

### Input & Authentication

- Garmin Connect account login
- Garmin API integration (python-garminconnect)
- Web scraping or dynamic data pull
- OAuth or token-based authentication
- Multiple Garmin accounts

### Data Storage

- SQLite database or persistent activity store
- Multi-activity history tracking or trending
- Activity deduplication logic
- Data caching between runs

### Output & Integration

- Web UI or dashboard
- Database schema or ORM
- Direct AI API uploads (ChatGPT, Claude, NotebookLM API)
- Cloud storage integration
- Webhook or event streaming
- Email or Slack notifications

### Feature Expansion

- Support for non-Running activities (Cycling, Swimming, Strength, etc.)
- TCX file modification or direct GPS redaction in-place
- Batch scheduling or watch-folder monitoring
- Configuration files or profiles
- Advanced machine learning or coaching recommendations
- Full coaching or medical advice engine

### Dependencies

- GarminDB as a dependency
- python-garminconnect as a dependency
- Heavy frameworks (Django, Flask, FastAPI)
- Real-time processing libraries

---

## Scope Locked

MVP accepts **only** manually exported TCX files from Garmin Connect for Running activities, and transforms them to JSON, CSV, and AI-ready Markdown outputs with configurable GPS privacy.

Any request to add features outside these bounds must be treated as a scope change, documented in a new decision or brief, and explicitly approved before implementation.

## Roadmap Reference

Candidates for **post-MVP** work are listed in `docs/04_architecture.md` sections 6.1–6.4 (personal database, GarminDB research, python-garminconnect research, Web UI). These remain research items and must not be added during MVP without explicit user approval.
