"""Pure Python helper functions for the Garmin TCX AI Local UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


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
