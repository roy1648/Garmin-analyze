"""Pure Python helper functions for the Garmin TCX AI Local UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import importlib
import os
from pathlib import Path
import subprocess
import sys


@dataclass(frozen=True)
class InputPathStatus:
    """Status representing the validity and contents of an input path."""

    is_valid: bool
    message: str
    tcx_count: int = 0


@dataclass(frozen=True)
class FolderOpenResult:
    """Result of attempting to open a folder with OS file manager."""

    success: bool
    message: str


def inspect_input_path(path_text: str) -> InputPathStatus:
    """Validate a local input path for one TCX file or a directory of TCX files.

    Args:
        path_text: The raw input path string.

    Returns:
        InputPathStatus with validation state and message.
    """
    stripped = path_text.strip()
    if not stripped:
        return InputPathStatus(
            is_valid=False,
            message="請輸入 TCX 檔案路徑或資料夾路徑。",
            tcx_count=0,
        )

    path = Path(stripped)
    if not path.exists():
        return InputPathStatus(
            is_valid=False,
            message=f"找不到路徑：{stripped}",
            tcx_count=0,
        )

    if path.is_file():
        if path.suffix.lower() == ".tcx":
            return InputPathStatus(
                is_valid=True,
                message=f"偵測到 1 個 TCX 檔案：{path.name}",
                tcx_count=1,
            )
        else:
            return InputPathStatus(
                is_valid=False,
                message=f"不是 .tcx 檔案：{path.name}",
                tcx_count=0,
            )

    if path.is_dir():
        tcx_count = 0
        try:
            for p in path.iterdir():
                if p.is_file() and p.suffix.lower() == ".tcx":
                    tcx_count += 1
        except Exception as exc:
            return InputPathStatus(
                is_valid=False,
                message=f"無法讀取資料夾內容：{exc}",
                tcx_count=0,
            )

        if tcx_count > 0:
            return InputPathStatus(
                is_valid=True,
                message=f"偵測到 {tcx_count} 個 TCX 檔案。",
                tcx_count=tcx_count,
            )
        else:
            return InputPathStatus(
                is_valid=False,
                message="資料夾內沒有 .tcx 檔案。",
                tcx_count=0,
            )

    return InputPathStatus(
        is_valid=False,
        message=f"無效的路徑類型：{stripped}",
        tcx_count=0,
    )


def normalize_output_path(path_text: str) -> Path:
    """Normalize output path text, falling back to default output dir if empty.

    Args:
        path_text: The output directory path string.

    Returns:
        A Path object.
    """
    stripped = path_text.strip()
    if not stripped:
        return default_output_dir()
    return Path(stripped)


def default_output_dir(base_dir: Path | None = None) -> Path:
    """Return a timestamped default UI output directory.

    Args:
        base_dir: Optional base path. Defaults to data/processed.

    Returns:
        A timestamped Path under the base directory.
    """
    root = base_dir or Path("data") / "processed"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root / f"ui_run_{timestamp}"


def read_text_if_exists(path: Path | None) -> str:
    """Read UTF-8 text if the path exists, otherwise return empty string.

    Args:
        path: Optional Path to read.

    Returns:
        The content of the file or an empty string.
    """
    if path is None or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def output_file_status(path: Path | None) -> str:
    """Return a small human-readable status for one output file.

    Args:
        path: Optional Path to check.

    Returns:
        A status string indicating whether the file exists.
    """
    if path is not None and path.is_file():
        return f"✅ {path}"
    return "未產生"


def read_output_text(path: Path | None) -> str:
    """Read an output file as UTF-8 text for preview/copy actions.

    Args:
        path: Optional Path to read.

    Returns:
        The content of the file or an empty string.
    """
    return read_text_if_exists(path)


def can_open_folder(path: Path | None) -> bool:
    """Return whether the output folder path exists and is a directory.

    Args:
        path: Optional Path to check.

    Returns:
        True if the path exists and is a directory, False otherwise.
    """
    if path is None:
        return False
    return path.exists() and path.is_dir()


def folder_open_command(path: Path, platform: str) -> list[str] | None:
    """Return the folder-open command for non-Windows platforms.

    Args:
        path: The directory path to open.
        platform: The system platform name (e.g. sys.platform).

    Returns:
        A list of command tokens or None.
    """
    if platform == "darwin":
        return ["open", str(path)]
    elif platform.startswith("linux"):
        return ["xdg-open", str(path)]
    return None


def open_folder(path: Path) -> FolderOpenResult:
    """Open a local folder with the OS default file manager.

    Args:
        path: The directory path to open.

    Returns:
        FolderOpenResult with success flag and message.
    """
    if not path.exists() or not path.is_dir():
        return FolderOpenResult(
            success=False,
            message=f"路徑不存在或不是資料夾：{path}",
        )

    try:
        plat = sys.platform
        abs_path = path.resolve()

        if plat.startswith("win"):
            abs_path_str = str(abs_path)
            # Try subprocess Popen with explorer first to bring it to foreground/top layer
            try:
                subprocess.Popen(["explorer", abs_path_str])
                return FolderOpenResult(
                    success=True,
                    message="已成功在最上層開啟輸出資料夾。",
                )
            except Exception as err:
                # Fallback to os.startfile
                if hasattr(os, "startfile"):
                    try:
                        os.startfile(abs_path_str)
                        return FolderOpenResult(
                            success=True,
                            message="已成功在檔案總管開啟輸出資料夾。",
                        )
                    except Exception as exc:
                        return FolderOpenResult(
                            success=False,
                            message=f"無法開啟資料夾：{exc}",
                        )
                else:
                    return FolderOpenResult(
                        success=False,
                        message=f"無法開啟資料夾且不支援 os.startfile：{err}",
                    )

        cmd = folder_open_command(abs_path, plat)
        if cmd is not None:
            subprocess.Popen(cmd)
            return FolderOpenResult(
                success=True,
                message="已成功在檔案瀏覽器開啟輸出資料夾。",
            )
        else:
            return FolderOpenResult(
                success=False,
                message=f"不支援的作業系統平台：{plat}",
            )
    except Exception as exc:
        return FolderOpenResult(
            success=False,
            message=f"開啟資料夾時發生錯誤：{exc}",
        )


# ---------------------------------------------------------------------------
# Native path picker helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DialogResult:
    """Result of a native file or folder dialog operation."""

    success: bool
    path_text: str
    message: str


def _create_hidden_tk_root():  # type: ignore[return]
    """Create and return a hidden Tk root window for native dialogs.

    This private function is extracted as a seam so that unit tests can
    monkeypatch it without needing a real display or tkinter installation.

    Returns:
        A hidden Tk root object, or raises an exception if unavailable.
    """
    import tkinter as tk  # lazy import – standard library only
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    return root


def select_tcx_file_dialog() -> DialogResult:
    """Open a native dialog for selecting one .tcx file.

    Uses Python standard library tkinter only (lazy import via importlib).
    Falls back gracefully when tkinter is unavailable (e.g., headless CI).

    Returns:
        DialogResult with success flag, selected path, and user message.
    """
    try:
        root = _create_hidden_tk_root()
        try:
            # Use importlib + sys.modules so that monkeypatch.setitem on
            # sys.modules["tkinter.filedialog"] works in headless CI tests.
            importlib.import_module("tkinter.filedialog")
            fd = sys.modules["tkinter.filedialog"]
            file_path: str = fd.askopenfilename(
                parent=root,
                title="選擇 TCX 檔案",
                filetypes=[("TCX files", "*.tcx"), ("All files", "*.*")],
            )
        finally:
            root.destroy()

        if file_path:
            return DialogResult(
                success=True,
                path_text=file_path,
                message=f"已選擇 TCX 檔案：{file_path}",
            )
        return DialogResult(
            success=False,
            path_text="",
            message="未選擇檔案。",
        )
    except Exception as exc:
        return DialogResult(
            success=False,
            path_text="",
            message=f"無法開啟檔案選擇器：{exc}",
        )


def select_directory_dialog(title: str = "選擇資料夾") -> DialogResult:
    """Open a native dialog for selecting a directory.

    Uses Python standard library tkinter only (lazy import via importlib).
    Falls back gracefully when tkinter is unavailable (e.g., headless CI).

    Args:
        title: The title shown in the native dialog window.

    Returns:
        DialogResult with success flag, selected path, and user message.
    """
    try:
        root = _create_hidden_tk_root()
        try:
            # Use importlib + sys.modules so that monkeypatch.setitem on
            # sys.modules["tkinter.filedialog"] works in headless CI tests.
            importlib.import_module("tkinter.filedialog")
            fd = sys.modules["tkinter.filedialog"]
            folder_path: str = fd.askdirectory(
                parent=root,
                title=title,
            )
        finally:
            root.destroy()

        if folder_path:
            return DialogResult(
                success=True,
                path_text=folder_path,
                message=f"已選擇資料夾：{folder_path}",
            )
        return DialogResult(
            success=False,
            path_text="",
            message="未選擇資料夾。",
        )
    except Exception as exc:
        return DialogResult(
            success=False,
            path_text="",
            message=f"無法開啟資料夾選擇器：{exc}",
        )
