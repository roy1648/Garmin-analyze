# Data Contract

## 1. Input Contract

### 1.1 Supported Input

Supported input:

- Garmin Connect exported `.tcx` files.

Supported activity type:

- Running

Input modes:

- Single file path.
- Folder path containing one or more `.tcx` files.

### 1.2 TCX Parsing Expectations

The parser should support:

- TCX XML namespaces.
- `TrainingCenterDatabase`.
- `Activities`.
- `Activity`.
- `Lap`.
- `Track`.
- `Trackpoint`.
- Garmin extension fields when known and useful.

Known Garmin extension fields may include:

- Speed
- Run cadence
- Average speed
- Average run cadence
- Watts

Unsupported extension fields may be skipped.

## 2. Output File Set

Each source activity should produce a file set under the output directory.

Recommended naming pattern:

```text
<activity_id>/
  activity.json
  trackpoints.csv
  ai_summary.json
  ai_summary.md
```

If an activity ID is unavailable, use a safe filename derived from the source filename.

## 3. `activity.json`

Purpose: full structured representation of one activity.

Required top-level structure:

```json
{
  "source": {},
  "privacy": {},
  "activity": {},
  "laps": [],
  "trackpoints": [],
  "warnings": []
}
```

### 3.1 `source`

```json
{
  "format": "tcx",
  "file_name": "activity.tcx",
  "file_path": "data/raw/activity.tcx"
}
```

### 3.2 `privacy`

```json
{
  "gps_policy": "keep"
}
```

Allowed `gps_policy` values:

- `keep`
- `remove`
- `redact_start_end`

Default:

- `keep`

### 3.3 `activity`

```json
{
  "sport": "Running",
  "activity_id": "2026-05-01T06:30:00Z",
  "start_time": "2026-05-01T06:30:00Z",
  "total_time_seconds": 3600.0,
  "distance_meters": 10000.0,
  "calories": 650,
  "average_heart_rate_bpm": 145,
  "maximum_heart_rate_bpm": 172,
  "maximum_speed_mps": 4.2
}
```

Missing standard values should be `null`.

### 3.4 `laps`

Each lap object:

```json
{
  "lap_index": 1,
  "start_time": "2026-05-01T06:30:00Z",
  "total_time_seconds": 1800.0,
  "distance_meters": 5000.0,
  "calories": 320,
  "average_heart_rate_bpm": 142,
  "maximum_heart_rate_bpm": 168,
  "maximum_speed_mps": 4.1,
  "intensity": "Active",
  "trigger_method": "Manual"
}
```

### 3.5 `trackpoints`

Each trackpoint object:

```json
{
  "trackpoint_index": 1,
  "lap_index": 1,
  "timestamp": "2026-05-01T06:30:01Z",
  "latitude": 25.0,
  "longitude": 121.0,
  "altitude_meters": 20.5,
  "distance_meters": 10.0,
  "heart_rate_bpm": 140,
  "speed_mps": 2.8,
  "pace_seconds_per_km": 357.1,
  "run_cadence_spm": 170,
  "power_watts": 230
}
```

GPS fields depend on `gps_policy`.

## 4. `trackpoints.csv`

Purpose: spreadsheet and data-analysis friendly trackpoint output.

Required columns:

```text
activity_id
lap_index
trackpoint_index
timestamp
latitude
longitude
altitude_meters
distance_meters
heart_rate_bpm
speed_mps
pace_seconds_per_km
run_cadence_spm
power_watts
```

CSV rules:

- Use UTF-8.
- Include header row.
- Missing values should be empty cells.
- GPS columns may be empty depending on `gps_policy`.

## 5. `ai_summary.json`

Purpose: compact, structured, AI-ready summary.

Required top-level structure:

```json
{
  "activity_summary": {},
  "key_metrics": {},
  "lap_summary": [],
  "trend_summary": {},
  "privacy": {},
  "data_quality": {},
  "ai_context": ""
}
```

### 5.1 Key Metrics

MVP key metrics:

- Duration in minutes
- Distance in kilometers
- Average pace as seconds per kilometer
- Average pace as `mm:ss/km`
- Average heart rate
- Maximum heart rate
- Minimum elevation
- Maximum elevation
- Estimated elevation gain
- Lap count

### 5.2 Trend Summary

MVP trend fields:

- First-half average pace
- Second-half average pace
- Pace trend
- First-half average heart rate
- Second-half average heart rate
- Heart-rate trend

Allowed simple trend labels:

- `faster_later`
- `slower_later`
- `stable`
- `insufficient_data`

## 6. `ai_summary.md`

Purpose: primary handoff document for ChatGPT, Claude, NotebookLM, or similar AI tools.

Recommended sections:

```markdown
# Running Activity Summary

## Activity

## Key Metrics

## Lap Summary

## Pace Trend

## Heart Rate Trend

## Elevation

## Data Quality Notes

## Privacy Notes

## Suggested AI Analysis Questions
```

The Markdown should be concise, factual, and avoid pretending to be a certified coach or medical professional.

## 7. Privacy Contract

GPS policy behavior:

- `keep`: keep latitude and longitude in JSON, CSV, and AI summaries where relevant.
- `remove`: set latitude and longitude to `null` in JSON, empty in CSV, and omit route details from Markdown.
- `redact_start_end`: remove or mask GPS coordinates near the beginning and end of the activity.

The output must record the selected GPS policy.

