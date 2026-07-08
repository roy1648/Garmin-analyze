# Known Limitations

## Current intended limits

- Local-only tool.
- No Garmin Connect API.
- No cloud sync.
- No login.
- No database.
- No charts.
- No AI coaching.
- No medical interpretation.
- No HR zone inference.
- No Garmin zone inference.
- No planned workout matching.
- No 課表角色推論.
- No EXE packaging yet.

## Data and privacy

- User is responsible for choosing GPS policy.
- `keep` preserves GPS coordinates.
- `redact_start_end` is the recommended default.
- Output files are written locally.
- No upload is performed by this project.

## UI limitations

- Native file picker depends on local OS / tkinter availability.
- If native picker fails, manual path input remains the fallback.
- Clipboard copy may depend on browser permission.
- Manual copy fallback is provided where needed.
- Streamlit UI is local development / local operator UI, not a packaged desktop app.

## Platform limitations

- Primary expected operating environment is Windows local machine.
- CI validates Linux automated tests, not Windows native UI behavior.
- Windows manual smoke test is required before release.
