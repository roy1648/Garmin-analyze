# Windows Packaging Spec Files

This folder contains PyInstaller specifications and version metadata used for compiling the Windows executables.

## Files

- **`garmin-tcx-ai-cli.spec`**: PyInstaller spec file for bundling the CLI entry point (`src/garmin_tcx_ai/cli.py`).
- **`garmin-tcx-ai-ui.spec`**: PyInstaller spec file for bundling the Streamlit Local UI application. It uses PyInstaller's `collect_all("streamlit")` utility to ensure all required assets and static files are bundled, and targets `src/garmin_tcx_ai/ui_exe_launcher.py` as the entry script.
- **`version_info.txt`**: Standard Windows version metadata definition (`VSVersionInfo`) that embeds metadata (version 0.1.0, copyright, company description) directly into the compiled `.exe` files.

## Design Decisions

1. **Folder-based Bundle (`onedir`)**: We intentionally target `--onedir` distribution (which is PyInstaller's default) instead of a single executable file (`--onefile`). Bundling a web application framework like Streamlit with its large HTML/JS assets and many binary dependencies into a single-file EXE often results in extremely slow startup times (due to on-the-fly unpacking to temp directories) and runtime path resolution issues. 
2. **Console Enabled**: We keep `console=True` for both CLI and UI builds to ensure startup errors, Streamlit CLI server logs, and diagnostic output are visible during this packaging spike.
3. **No Installer / No Release Tagging**: We focus exclusively on local build verification and do not configure installers (like Inno Setup) or automated GitHub releases.
4. **Human-Run Builds Only**: To prevent large build log transfers and massive memory/token usage during agent execution, actual packaging command runs are reserved for the human operator on their local Windows machine.

## How to Build

Please run the build script from the project root:

```cmd
scripts\build_exe.manual.cmd
```

## Optional Dependencies & Local Verification

The PyInstaller spec files are configured to bundle the optional Garmin Connect dependencies (`garminconnect`, `curl_cffi`, and `keyring`).

To ensure safety:
- **Manual Verification Only**: Real logins to Garmin Connect and credential operations in the Windows Credential Manager are verified manually by local operators.
- **No CI Integration**: The automated test suites and CI pipelines do not perform real logins or access the Windows Credential Manager.
