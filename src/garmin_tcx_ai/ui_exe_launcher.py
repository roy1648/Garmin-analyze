"""Launch the local Streamlit UI from source or from a packaged EXE.

The launcher picks a free TCP port (so a stale or foreign Streamlit
process on 8501 no longer blocks start-up), prints the exact URL, and
opens the default browser once the server is listening.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PREFERRED_PORT = 8501
_BROWSER_WAIT_SECONDS = 20.0


def _resource_root() -> Path:
    """Resolve the root directory where application resources are located.

    In frozen mode (e.g., PyInstaller packaging), it points to the temporary
    extraction path sys._MEIPASS. In source mode, it points to the project
    root.
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


def _port_is_free(port: int, host: str = "localhost") -> bool:
    """Return True when nothing accepts connections on *host*:*port*.

    A connect probe is used instead of a bind probe because on Windows a
    bind can succeed even while another process is already listening on
    the same port (for example a dual-stack ``::`` listener).
    """
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return False
    except OSError:
        return True


def _find_free_port(preferred: int = PREFERRED_PORT) -> int:
    """Return *preferred* when free, otherwise an OS-assigned free port."""
    if _port_is_free(preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, timeout: float) -> bool:
    """Poll *url* until it answers or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0):
                return True
        except (OSError, ValueError):
            time.sleep(0.5)
    return False


def _open_browser_when_ready(url: str) -> None:
    """Open the default browser after the Streamlit server is up."""
    if _wait_for_server(url, _BROWSER_WAIT_SECONDS):
        webbrowser.open(url)


def _start_browser_thread(url: str) -> threading.Thread:
    """Start a daemon thread that opens the browser when ready."""
    thread = threading.Thread(
        target=_open_browser_when_ready,
        args=(url,),
        daemon=True,
    )
    thread.start()
    return thread


def main(open_browser: bool = True) -> int:
    """Launch the Streamlit local UI application.

    Args:
        open_browser: When True, open the default browser automatically
            once the server responds.

    Returns:
        Process exit code.
    """
    import os

    from streamlit.web import cli as stcli

    # Force development mode off so a custom server port is accepted in
    # a packaged environment.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    root = _resource_root()
    src_path = _ensure_app_import_path(root)
    existing_pythonpath = os.environ.get("PYTHONPATH")
    if existing_pythonpath:
        os.environ["PYTHONPATH"] = (
            f"{src_path}{os.pathsep}{existing_pythonpath}"
        )
    else:
        os.environ["PYTHONPATH"] = str(src_path)

    app_path = root / "src" / "garmin_tcx_ai" / "ui_streamlit.py"

    if not app_path.is_file():
        print(
            f"[ERROR] Cannot find Streamlit app: {app_path}",
            file=sys.stderr,
        )
        return 1

    port = _find_free_port()
    url = f"http://localhost:{port}"
    if port != PREFERRED_PORT:
        print(
            f"[INFO] Port {PREFERRED_PORT} is busy; using port {port}."
        )
    print(f"[INFO] Garmin TCX AI UI: {url}")
    print("[INFO] Close this window to stop the app.")

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]

    if open_browser:
        _start_browser_thread(url)

    stcli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
