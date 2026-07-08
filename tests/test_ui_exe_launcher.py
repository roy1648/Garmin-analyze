"""Unit tests for the packaged Streamlit UI launcher."""

from __future__ import annotations

import sys
import types
import os
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
    monkeypatch.setattr(sys, "path", ["existing"])
    monkeypatch.delenv("PYTHONPATH", raising=False)

    exit_code = ui_exe_launcher.main()

    src_text = str(tmp_path / "src")
    assert exit_code == 0
    assert called == [True]
    assert sys.path[0] == src_text
    assert os.environ["PYTHONPATH"] == src_text
    assert sys.argv[:3] == ["streamlit", "run", str(app_path)]
