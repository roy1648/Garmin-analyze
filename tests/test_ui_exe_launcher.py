"""Unit tests for the packaged Streamlit UI launcher."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

from garmin_tcx_ai import ui_exe_launcher


def test_ui_pyinstaller_spec_includes_tk_filedialog() -> None:
    """UI EXE bundle includes the native file picker module."""
    spec_path = Path("packaging") / "garmin-tcx-ai-ui.spec"
    spec_text = spec_path.read_text(encoding="utf-8")

    assert "'tkinter.filedialog'" in spec_text


def test_ensure_app_import_path_prepends_bundled_src(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Bundled src path is added before Streamlit runs the app file."""
    original_path = list(sys.path)
    monkeypatch.setattr(sys, "path", original_path.copy())

    src_path = ui_exe_launcher._ensure_app_import_path(tmp_path)

    assert src_path == tmp_path / "src"
    assert sys.path[0] == str(src_path)


def test_ensure_app_import_path_is_idempotent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Repeated launcher setup does not duplicate the src path."""
    src_text = str(tmp_path / "src")
    monkeypatch.setattr(sys, "path", [src_text, "existing"])

    ui_exe_launcher._ensure_app_import_path(tmp_path)

    assert sys.path == [src_text, "existing"]


def test_main_sets_import_path_before_streamlit_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Launcher prepares imports before delegating to Streamlit CLI."""
    app_path = tmp_path / "src" / "garmin_tcx_ai" / "ui_streamlit.py"
    app_path.parent.mkdir(parents=True)
    app_path.write_text("pass\n", encoding="utf-8")

    called = []

    def fake_streamlit_main() -> None:
        called.append(True)

    fake_cli = types.SimpleNamespace(main=fake_streamlit_main)
    fake_web = types.ModuleType("streamlit.web")
    fake_web.cli = fake_cli
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.web = fake_web

    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "streamlit.web", fake_web)
    monkeypatch.setattr(ui_exe_launcher, "_resource_root", lambda: tmp_path)
    monkeypatch.setattr(ui_exe_launcher, "_find_free_port", lambda: 8765)
    monkeypatch.setattr(sys, "path", ["existing"])
    monkeypatch.delenv("PYTHONPATH", raising=False)

    exit_code = ui_exe_launcher.main(open_browser=False)

    src_text = str(tmp_path / "src")
    assert exit_code == 0
    assert called == [True]
    assert sys.path[0] == src_text
    assert os.environ["PYTHONPATH"] == src_text
    assert sys.argv[:3] == ["streamlit", "run", str(app_path)]
    assert "--server.port=8765" in sys.argv


def test_find_free_port_prefers_default_when_free(monkeypatch) -> None:
    """The preferred port is returned when nothing is bound to it."""
    monkeypatch.setattr(ui_exe_launcher, "_port_is_free", lambda p: True)

    assert ui_exe_launcher._find_free_port() == ui_exe_launcher.PREFERRED_PORT


def test_find_free_port_falls_back_when_busy() -> None:
    """A busy preferred port yields a different, bindable port."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        busy_port = blocker.getsockname()[1]

        chosen = ui_exe_launcher._find_free_port(preferred=busy_port)

    assert chosen != busy_port
    assert 1024 < chosen < 65536


def test_main_opens_browser_thread_by_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """main() starts the browser thread with the chosen URL."""
    app_path = tmp_path / "src" / "garmin_tcx_ai" / "ui_streamlit.py"
    app_path.parent.mkdir(parents=True)
    app_path.write_text("pass\n", encoding="utf-8")

    fake_cli = types.SimpleNamespace(main=lambda: None)
    fake_web = types.ModuleType("streamlit.web")
    fake_web.cli = fake_cli
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.web = fake_web
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setitem(sys.modules, "streamlit.web", fake_web)
    monkeypatch.setattr(ui_exe_launcher, "_resource_root", lambda: tmp_path)
    monkeypatch.setattr(ui_exe_launcher, "_find_free_port", lambda: 9001)
    opened: list[str] = []
    monkeypatch.setattr(
        ui_exe_launcher,
        "_start_browser_thread",
        lambda url: opened.append(url),
    )

    assert ui_exe_launcher.main() == 0
    assert opened == ["http://localhost:9001"]
