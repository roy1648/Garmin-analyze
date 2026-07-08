from __future__ import annotations

from pathlib import Path
import sys


def _resource_root() -> Path:
    """Resolve the root directory where application resources are located.

    In frozen mode (e.g., PyInstaller packaging), it points to the temporary
    extraction path sys._MEIPASS. In source mode, it points to the project root.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def main() -> int:
    """Launch the Streamlit local UI application.

    This acts as a programmatic entry point for launching streamlit within
    a packaged executable.
    """
    from streamlit.web import cli as stcli

    root = _resource_root()
    app_path = root / "src" / "garmin_tcx_ai" / "ui_streamlit.py"

    if not app_path.is_file():
        print(f"[ERROR] Cannot find Streamlit app: {app_path}", file=sys.stderr)
        return 1

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]

    stcli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
