# Requirements

## 1. Functional Requirements

### 1.1 TCX Input

The tool must support:

- A single `.tcx` file as input.
- A folder containing multiple `.tcx` files as input.
- Ignoring or warning about non-TCX files in folder mode.

The tool must not modify the original TCX files.

### 1.2 Activity Scope

The MVP must support Running activities.

If the input TCX contains another activity type:

- The tool should detect it when possible.
- The tool should not silently treat it as Running.
- The tool may skip it with a clear warning in MVP.

### 1.3 Parsed Data

The tool should parse the following activity-level fields when available:

- Sport type
- Activity ID or start time
- Start time
- Total time in seconds
- Distance in meters
- Calories
- Average heart rate
- Maximum heart rate
- Maximum speed

The tool should parse the following lap-level fields when available:

- Lap start time
- Total time in seconds
- Distance in meters
- Calories
- Average heart rate
- Maximum heart rate
- Maximum speed
- Intensity
- Trigger method

The tool should parse the following trackpoint-level fields when available:

- Timestamp
- Latitude
- Longitude
- Altitude in meters
- Distance in meters
- Heart rate
- Speed
- Running cadence
- Power

### 1.4 Output Formats

For each converted activity, the tool must produce:

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`

In batch mode, each TCX file should produce its own output set.

### 1.5 AI-ready Summary

The AI-ready summary must include:

- Basic activity metadata
- Distance
- Duration
- Average pace
- Average heart rate
- Maximum heart rate
- Elevation summary
- Lap summary
- First-half versus second-half pace trend
- First-half versus second-half heart-rate trend
- GPS privacy policy used
- Notes about missing data

The AI-ready summary must avoid making medical or professional coaching claims.

### 1.6 Missing Data

If a standard field is missing:

- JSON output should use `null`.
- CSV output should leave the cell empty.
- AI summary should mention missing data only when it affects interpretation.

If an unknown or unsupported extension field appears:

- The tool may skip it.
- The tool should record a warning when practical.
- The conversion should continue.

## 2. Non-functional Requirements

### 2.1 Maintainability

The project must be maintainable by one developer.

Implementation should favor:

- Small modules
- Clear function boundaries
- Explicit data contracts
- Minimal dependencies
- No unnecessary framework

### 2.2 Python Standards

Future Python code must follow:

- PEP8 style
- Type hints for public functions and data structures
- Docstrings for modules, classes, and public functions
- Clear names; avoid one-letter variable names

### 2.3 Local-first Data Handling

The tool must work locally.

The MVP must not:

- Upload data to cloud services.
- Authenticate to Garmin Connect.
- Store data in a database.
- Send data directly to AI APIs.

### 2.4 Privacy

The tool must treat GPS and health data as sensitive.

Required privacy behavior:

- Raw TCX files are read-only inputs.
- GPS policy is explicit and recorded in AI-ready outputs.
- Heart rate, pace, and distance are preserved unless future settings say otherwise.
- Documentation must explain the risk of sharing GPS and health data with AI applications.

### 2.5 Error Handling

Errors should be readable and actionable.

The tool should distinguish:

- File not found
- Unsupported file type
- Invalid XML
- Valid TCX with unsupported activity type
- Missing optional data
- Output write failure

## 3. MVP Boundaries

The MVP must not implement:

- Web UI
- SQLite or other database
- GarminDB integration
- python-garminconnect integration
- Garmin Connect login
- NotebookLM or ChatGPT API upload
- Full training recommendation engine

These may appear in roadmap documentation only.

