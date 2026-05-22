# Acceptance Tests

This document defines behavior-level acceptance tests. It does not contain test code.

## 1. Single TCX Conversion

Given a valid Garmin Connect Running TCX file  
When the user converts the file  
Then the output directory contains:

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`

And the original TCX file is not modified.

## 2. Folder Batch Conversion

Given a folder containing multiple `.tcx` files  
When the user converts the folder  
Then each valid Running TCX file produces one output file set.

And non-TCX files are skipped or warned about without stopping the batch.

## 3. Running Activity Only

Given a valid TCX file with sport type `Running`  
When the user converts the file  
Then the file is processed.

Given a valid TCX file with another sport type  
When the user converts the file  
Then the file is skipped or rejected with a clear unsupported activity warning.

## 4. Missing Heart Rate

Given a Running TCX file without heart-rate data  
When the user converts the file  
Then:

- JSON heart-rate fields are `null`.
- CSV heart-rate cells are empty.
- AI summary includes a data quality note if heart-rate trend cannot be calculated.
- Conversion does not fail.

## 5. Missing GPS

Given a Running TCX file without GPS coordinates  
When the user converts the file  
Then:

- JSON latitude and longitude fields are `null`.
- CSV latitude and longitude cells are empty.
- AI summary states that route analysis is unavailable.
- Conversion does not fail.

## 6. Missing Elevation

Given a Running TCX file without elevation data  
When the user converts the file  
Then:

- Elevation fields are `null` or empty.
- Elevation gain is `null`.
- AI summary includes an elevation data quality note.
- Conversion does not fail.

## 7. Multi-lap Activity

Given a Running TCX file with multiple laps  
When the user converts the file  
Then:

- `activity.json` contains all laps in order.
- `ai_summary.json` contains lap summaries.
- `ai_summary.md` presents lap summaries clearly.

## 8. Invalid XML

Given a malformed XML file with `.tcx` extension  
When the user converts the file  
Then:

- The tool reports an invalid XML error.
- No misleading partial output is produced for that file.
- Batch mode continues to the next file when possible.

## 9. GPS Policy: keep

Given a Running TCX file with GPS data  
And GPS policy is `keep`  
When the user converts the file  
Then:

- Latitude and longitude are present in `activity.json`.
- Latitude and longitude are present in `trackpoints.csv`.
- `ai_summary.json` records `gps_policy` as `keep`.
- `ai_summary.md` includes a privacy note that GPS was preserved.

## 10. GPS Policy: remove

Given a Running TCX file with GPS data  
And GPS policy is `remove`  
When the user converts the file  
Then:

- Latitude and longitude are removed or set to `null` in JSON.
- Latitude and longitude cells are empty in CSV.
- AI summaries do not expose coordinates.
- `ai_summary.json` records `gps_policy` as `remove`.

## 11. GPS Policy: redact_start_end

Given a Running TCX file with GPS data  
And GPS policy is `redact_start_end`  
When the user converts the file  
Then:

- GPS coordinates near the beginning and end of the activity are removed or masked.
- Mid-route GPS coordinates may remain.
- AI summaries record that start and end route data was redacted.

## 12. AI-ready Markdown

Given a successful conversion  
When `ai_summary.md` is opened  
Then it contains:

- Activity summary
- Key metrics
- Lap summary
- Pace trend
- Heart-rate trend
- Elevation summary
- Data quality notes
- Privacy notes
- Suggested AI analysis questions

## 13. Done Criteria

The MVP is done when:

- Valid Running TCX files convert successfully.
- Single-file and folder modes are supported.
- All four output formats are produced.
- Missing optional fields do not break conversion.
- GPS policy is implemented and recorded.
- Original TCX files are never modified.
- Acceptance scenarios above can be mapped directly to pytest tests.

