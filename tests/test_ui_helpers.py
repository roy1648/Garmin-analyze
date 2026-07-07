"""Unit tests for Garmin TCX AI Local UI helpers."""

from __future__ import annotations

from pathlib import Path

from garmin_tcx_ai.ui_helpers import (
    default_output_dir,
    output_file_status,
    read_text_if_exists,
)


def test_read_text_if_exists_returns_empty_for_missing_path() -> None:
    """Test read_text_if_exists returns empty string for missing paths."""
    assert read_text_if_exists(None) == ""
    assert read_text_if_exists(Path("nonexistent_file_xyz.txt")) == ""


def test_read_text_if_exists_reads_existing_file(tmp_path: Path) -> None:
    """Test read_text_if_exists reads text from an existing file."""
    temp_file = tmp_path / "test.txt"
    content = "Hello Garmin Connect ETL"
    temp_file.write_text(content, encoding="utf-8")

    assert read_text_if_exists(temp_file) == content


def test_output_file_status_for_existing_file(tmp_path: Path) -> None:
    """Test output_file_status returns correct message for existing files."""
    temp_file = tmp_path / "existing.json"
    temp_file.write_text("{}", encoding="utf-8")

    status = output_file_status(temp_file)
    assert status == f"✅ {temp_file}"


def test_output_file_status_for_missing_file() -> None:
    """Test output_file_status returns correct message for missing files."""
    assert output_file_status(None) == "未產生"
    assert output_file_status(Path("missing_file_xyz.json")) == "未產生"


def test_default_output_dir_uses_data_processed_prefix(tmp_path: Path) -> None:
    """Test default_output_dir generates path with expected prefix."""
    # Test with custom base_dir
    res_custom = default_output_dir(tmp_path)
    assert res_custom.parent == tmp_path
    assert res_custom.name.startswith("ui_run_")

    # Test with default (None)
    res_default = default_output_dir()
    assert res_default.parent == Path("data") / "processed"
    assert res_default.name.startswith("ui_run_")
