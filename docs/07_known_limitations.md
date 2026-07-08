# Known Limitations

## Current intended limits

- Local-only tool.
- No official Garmin Developer Program API (local unofficial import is supported).
- No cloud sync.
- No automated/server-side login (local manual user login only).
- No database.
- No charts.
- No AI coaching.
- No medical interpretation.
- No HR zone inference.
- No Garmin zone inference.
- No planned workout matching.
- No 課表角色推論.
- No standalone onefile EXE / desktop installer (onedir EXE packaging is supported).

## Data and privacy

- User is responsible for choosing GPS policy.
- `keep` preserves GPS coordinates.
- `redact_start_end` is the recommended default.
- Output files are written locally.
- No upload is performed by this project.

## UI limitations

- Native file picker depends on local OS / tkinter availability.
- If native picker fails, manual path input remains the fallback.
- Clipboard copy depends on browser-side copy functionality and permissions.
- If browser-side clipboard copy fails, the user can manually select and copy the text directly from the rendered preview/output on the page.
- Streamlit UI can be run via Python or as a packaged `onedir` EXE.

## Platform limitations

- Primary expected operating environment is Windows local machine.
- CI validates Linux automated tests, not Windows native UI behavior.
- Windows manual smoke test is required before release.
