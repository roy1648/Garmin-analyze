"""Pure Python helper functions for the Garmin TCX AI Local UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class InputPathStatus:
    """Status representing the validity and contents of an input path."""

    is_valid: bool
    message: str
    tcx_count: int = 0


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
