# Architecture

## 1. Design Principles

The project should remain small and maintainable by one developer.

The MVP should avoid:

- Heavy frameworks
- Web UI
- Database storage
- Garmin Connect login
- Garmin API integration
- Direct AI API upload

These are not rejected permanently. They are deferred until the TCX conversion pipeline is stable.

## 2. MVP Components

Recommended future Python structure:

```text
src/
  garmin_tcx_ai/
    parser.py
    models.py
    normalizer.py
    exporters.py
    summary.py
    privacy.py
scripts/
  convert_tcx.py
tests/
  fixtures/
```

This is a suggested implementation structure, not a requirement for the current documentation-only phase.

## 3. Component Responsibilities

### 3.1 Parser

Responsible for:

- Reading TCX XML.
- Handling XML namespaces.
- Extracting activity, lap, and trackpoint fields.
- Extracting known Garmin extension fields.
- Producing raw parsed objects or dictionaries.

The parser should not:

- Write output files.
- Apply AI summary logic.
- Modify privacy policy.

### 3.2 Normalizer

Responsible for:

- Converting parsed TCX values into the internal data contract.
- Normalizing units.
- Calculating derived values such as pace.
- Preserving missing values as `null` or empty cells later.

### 3.3 Privacy

Responsible for:

- Applying GPS policy.
- Ensuring output records which GPS policy was used.
- Avoiding accidental coordinate leaks in AI-ready summaries.

Supported policies:

- `keep`
- `remove`
- `redact_start_end`

### 3.4 Exporters

Responsible for producing:

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`

Exporters should not parse TCX directly.

### 3.5 Summary Builder

Responsible for:

- Key metrics.
- Lap summary.
- First-half versus second-half pace trend.
- First-half versus second-half heart-rate trend.
- Data quality notes.
- Suggested AI analysis questions.

The summary builder should remain factual and avoid medical or professional coaching claims.

### 3.6 Script Entrypoint

The MVP may start with a simple script.

Future command shape:

```bash
python scripts/convert_tcx.py --input data/raw/activity.tcx --output-dir data/processed --gps-policy keep
```

Batch example:

```bash
python scripts/convert_tcx.py --input data/raw --output-dir data/processed --gps-policy keep
```

The script should be designed so it can later evolve into a proper CLI without rewriting core logic.

## 4. Data Flow

```text
TCX file or folder
  -> input discovery
  -> TCX parser
  -> normalizer
  -> privacy policy
  -> summary builder
  -> JSON / CSV / Markdown exporters
```

Raw TCX files are read-only throughout the flow.

## 5. Dependency Strategy

Start with the Python standard library when practical.

Potential future dependencies:

- `pydantic` for stricter data models.
- `pandas` for richer CSV or analysis workflows.
- `typer` for a more polished CLI.
- `pytest` for automated tests.

Dependencies should be added only when they reduce complexity rather than increase it.

## 6. Future Architecture Options

### 6.1 Personal Database

A future version may add a small SQLite database for:

- Activity history
- Trend analysis
- Multi-activity comparison
- Faster local queries

This should be a separate phase after file-based conversion is stable.

### 6.2 GarminDB Research

GarminDB may be evaluated as a future reference or integration path for Garmin data import, SQLite storage, analysis, and Jupyter-style workflows.

MVP must not depend on GarminDB.

Reference:

- https://github.com/tcgoetz/GarminDB

### 6.3 python-garminconnect Research

python-garminconnect may be evaluated later for Garmin Connect API access, activity data, health data, historical data, and token workflows.

MVP must not authenticate to Garmin Connect or depend on python-garminconnect.

Reference:

- https://github.com/cyberjunky/python-garminconnect

### 6.4 Web UI

A Web UI may be useful later, but it is outside the MVP.

The file-based conversion pipeline should be completed before any UI work begins.

