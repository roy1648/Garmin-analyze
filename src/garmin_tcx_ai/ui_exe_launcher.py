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


def _ensure_app_import_path(root: Path) -> Path:
    """Ensure bundled source files are importable by Streamlit reruns."""
    src_path = root / "src"
    src_text = str(src_path)
    if src_text not in sys.path:
        sys.path.insert(0, src_text)
    return src_path


def main() -> int:
    """Launch the Streamlit local UI application.

    This acts as a programmatic entry point for launching streamlit within
    a packaged executable.
    """
    import os
    from streamlit.web import cli as stcli

    # Force development mode to false to allow setting custom server port in packaged environment.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    root = _resource_root()
    src_path = _ensure_app_import_path(root)
    existing_pythonpath = os.environ.get("PYTHONPATH")
    if existing_pythonpath:
        os.environ["PYTHONPATH"] = f"{src_path}{os.pathsep}{existing_pythonpath}"
    else:
        os.environ["PYTHONPATH"] = str(src_path)

    app_path = root / "src" / "garmin_tcx_ai" / "ui_streamlit.py"

    if not app_path.is_file():
        print(f"[ERROR] Cannot find Streamlit app: {app_path}", file=sys.stderr)
        return 1

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ]

    stcli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
