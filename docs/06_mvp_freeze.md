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
