# Project Brief: Garmin TCX AI-ready Converter

## 1. Project Goal

Build a small, personal Python tool that converts Garmin Connect exported TCX files into AI-ready data formats for later running training analysis.

The first version must focus on stable data conversion, not on building a complete AI coaching platform.

## 2. Context

The user manually exports TCX files from Garmin Connect. These files contain workout data such as:

- Activity type
- Start time and lap time
- Distance
- Heart rate
- Pace and speed
- Elevation
- GPS coordinates
- Garmin extension fields, such as running cadence, speed, and power when available

TCX is XML-based and useful as an export format, but it is not ideal for direct AI consumption. The project should transform TCX into formats that are easier for ChatGPT, Claude, NotebookLM, and future local analysis tools to read.

## 3. Primary User

The primary user is a solo developer building a personal workflow.

This project should therefore optimize for:

- Simple structure
- Low maintenance cost
- Clear files and contracts
- Easy Codex Agent collaboration
- Local-first data handling
- Avoiding premature platform design

## 4. MVP Scope

The MVP supports:

- Garmin Connect exported `.tcx` files
- Running activities only
- Single-file conversion
- Folder-based batch conversion
- Conversion into AI-readable and machine-readable output
- Configurable GPS privacy behavior

The MVP does not include:

- Web UI
- Database storage
- Garmin account login
- Garmin API integration
- Cloud sync
- Multi-user support
- Full AI coaching or medical-grade training advice

## 5. AI-ready Output Strategy

The primary AI-ready output should combine:

- Markdown for human and AI readability
- JSON for structure, validation, and future programmatic workflows

CSV remains useful for spreadsheet-style analysis but is not the primary AI handoff format.

## 6. Privacy Position

Garmin activity data may contain sensitive health and location information.

For the MVP:

- Raw TCX files must never be modified.
- Heart rate, pace, and distance are preserved in output.
- GPS coordinates are preserved by default because the selected default policy is `keep`.
- The tool must still support a GPS policy parameter so the user can choose safer output modes.
- AI-ready output must explicitly state which GPS policy was used.

Supported GPS policies:

- `keep`: preserve all GPS coordinates.
- `remove`: remove all GPS coordinates from AI-ready outputs.
- `redact_start_end`: remove or mask the beginning and ending parts of the route.

## 7. Future Roadmap

The first version should not implement database or API integrations, but the architecture should leave room for them.

Future candidates:

- A small personal SQLite activity database.
- GarminDB: https://github.com/tcgoetz/GarminDB
- python-garminconnect: https://github.com/cyberjunky/python-garminconnect

These are research and extension paths only. They must not affect the MVP requirement that manually exported TCX files remain the first supported input source.

