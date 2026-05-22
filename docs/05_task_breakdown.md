# Task Breakdown

This document breaks future implementation into small tasks suitable for solo development and Codex Agent collaboration.

No task in this document should be interpreted as permission to overbuild beyond the MVP.

## Phase 1: Project Skeleton

Goal:

- Create a minimal Python project structure.

Inputs:

- Existing specification files.

Outputs:

- Source folder.
- Script folder.
- Test folder.
- README update.

Done when:

- The project has a clear place for parser, models, exporters, summaries, and tests.
- No TCX conversion logic is required yet.

## Phase 2: Fixture Management

Goal:

- Establish safe test fixture handling.

Inputs:

- Local Garmin TCX examples.

Outputs:

- A sanitized or minimal TCX fixture for tests.
- Clear rule that raw personal TCX files are not modified.

Done when:

- Tests can be written without exposing unnecessary personal GPS or health data.

## Phase 3: TCX Parser

Goal:

- Parse Running TCX files into raw structured data.

Inputs:

- `.tcx` file path.

Outputs:

- Parsed activity, lap, and trackpoint data.
- Warnings for skipped or missing optional fields.

Done when:

- Running activity fields can be read.
- Lap and trackpoint collections preserve order.
- Invalid XML produces a readable error.

## Phase 4: Data Models

Goal:

- Define internal activity, lap, trackpoint, privacy, and warning structures.

Inputs:

- Parser output.

Outputs:

- Normalized internal data structures.

Done when:

- Missing standard fields can be represented as `None`.
- Public structures use type hints.
- Data names match `docs/02_data_contract.md`.

## Phase 5: JSON Exporter

Goal:

- Write `activity.json`.

Inputs:

- Normalized activity data.

Outputs:

- JSON following the data contract.

Done when:

- Output includes `source`, `privacy`, `activity`, `laps`, `trackpoints`, and `warnings`.
- Missing values are represented as `null`.

## Phase 6: CSV Exporter

Goal:

- Write `trackpoints.csv`.

Inputs:

- Normalized trackpoint data.

Outputs:

- UTF-8 CSV with required header row.

Done when:

- Required columns match `docs/02_data_contract.md`.
- Missing values become empty cells.

## Phase 7: AI Summary Builder

Goal:

- Create `ai_summary.json` and `ai_summary.md`.

Inputs:

- Normalized activity data.

Outputs:

- Structured summary JSON.
- Concise Markdown summary.

Done when:

- Key metrics are present.
- Lap summary is present.
- First-half and second-half pace trend is present when possible.
- First-half and second-half heart-rate trend is present when possible.
- Data quality and privacy notes are present.

## Phase 8: Batch Processing

Goal:

- Convert all TCX files in a folder.

Inputs:

- Folder path.

Outputs:

- One output file set per valid Running TCX.
- Warnings for skipped files.

Done when:

- A bad file does not stop the whole batch when continuation is possible.

## Phase 9: Acceptance Tests

Goal:

- Translate `docs/03_acceptance_tests.md` into automated tests.

Inputs:

- Fixtures.
- Conversion code.

Outputs:

- pytest test suite.

Done when:

- Key success and failure scenarios are covered.
- Tests confirm raw TCX files are not modified.

## Phase 10: README

Goal:

- Document how to use the MVP.

Inputs:

- Working conversion script.

Outputs:

- README with setup, usage, examples, privacy warning, and known limitations.

Done when:

- A future user can run single-file and folder conversion from the README.

## Future Tasks

These tasks are intentionally outside the MVP.

### SQLite Activity Store

Research and design a personal SQLite database for multi-activity history and trend analysis.

Do not start until file-based conversion is stable.

### GarminDB Research

Evaluate GarminDB as a reference or possible integration path.

Research questions:

- Does it duplicate or replace the local TCX parser?
- Can it help with SQLite activity history?
- Does it add too much operational complexity for a solo project?

Reference:

- https://github.com/tcgoetz/GarminDB

### python-garminconnect Research

Evaluate python-garminconnect for future Garmin Connect API access.

Research questions:

- What authentication and token handling are required?
- Which activity and health endpoints are useful?
- What privacy and reliability risks does API access introduce?

Reference:

- https://github.com/cyberjunky/python-garminconnect

### Web UI

Consider only after:

- TCX conversion is stable.
- Output contracts are proven useful.
- The user has repeated workflows that justify UI investment.

