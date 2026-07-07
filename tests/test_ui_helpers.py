"""Unit tests for Garmin TCX AI Local UI helpers."""

from __future__ import annotations

from pathlib import Path

from garmin_tcx_ai.ui_helpers import (
    default_output_dir,
    inspect_input_path,
    normalize_output_path,
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


def test_inspect_input_path_empty() -> None:
    """Test inspect_input_path with empty inputs."""
    res = inspect_input_path("")
    assert not res.is_valid
    assert res.tcx_count == 0
    assert "請輸入 TCX 檔案路徑或資料夾路徑" in res.message

    res_spaces = inspect_input_path("   ")
    assert not res_spaces.is_valid
    assert res_spaces.tcx_count == 0
    assert "請輸入 TCX 檔案路徑或資料夾路徑" in res_spaces.message


def test_inspect_input_path_missing() -> None:
    """Test inspect_input_path with a non-existent path."""
    res = inspect_input_path("nonexistent_path_xyz_123")
    assert not res.is_valid
    assert res.tcx_count == 0
    assert "找不到路徑" in res.message


def test_inspect_input_path_existing_tcx(tmp_path: Path) -> None:
    """Test inspect_input_path with an existing .tcx file."""
    tcx_file = tmp_path / "activity.tcx"
    tcx_file.write_text("<TCX></TCX>", encoding="utf-8")

    res = inspect_input_path(str(tcx_file))
    assert res.is_valid
    assert res.tcx_count == 1
    assert "偵測到 1 個 TCX 檔案" in res.message


def test_inspect_input_path_existing_non_tcx(tmp_path: Path) -> None:
    """Test inspect_input_path with an existing non-TCX file."""
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("not a tcx", encoding="utf-8")

    res = inspect_input_path(str(txt_file))
    assert not res.is_valid
    assert res.tcx_count == 0
    assert "不是 .tcx 檔案" in res.message


def test_inspect_input_path_directory_with_tcx_files(tmp_path: Path) -> None:
    """Test inspect_input_path with a directory containing .tcx files."""
    (tmp_path / "activity1.tcx").write_text("<TCX></TCX>", encoding="utf-8")
    (tmp_path / "activity2.TCX").write_text("<TCX></TCX>", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not a tcx", encoding="utf-8")

    res = inspect_input_path(str(tmp_path))
    assert res.is_valid
    assert res.tcx_count == 2
    assert "偵測到 2 個 TCX 檔案" in res.message


def test_inspect_input_path_directory_without_tcx_files(
    tmp_path: Path,
) -> None:
    """Test inspect_input_path with a directory containing no .tcx files."""
    (tmp_path / "notes.txt").write_text("not a tcx", encoding="utf-8")

    res = inspect_input_path(str(tmp_path))
    assert not res.is_valid
    assert res.tcx_count == 0
    assert "資料夾內沒有 .tcx 檔案" in res.message


def test_inspect_input_path_directory_scan_first_level_only(
    tmp_path: Path,
) -> None:
    """Test inspect_input_path checks only the first-level files in directory."""
    # First level tcx
    (tmp_path / "first_level.tcx").write_text("<TCX></TCX>", encoding="utf-8")

    # Nested folder with tcx
    sub_dir = tmp_path / "subfolder"
    sub_dir.mkdir()
    (sub_dir / "nested.tcx").write_text("<TCX></TCX>", encoding="utf-8")

    res = inspect_input_path(str(tmp_path))
    assert res.is_valid
    assert res.tcx_count == 1  # Should only detect first_level.tcx
    assert "偵測到 1 個 TCX 檔案" in res.message


def test_normalize_output_path_fallback() -> None:
    """Test normalize_output_path falls back to default output directory if empty."""
    res_empty = normalize_output_path("")
    assert res_empty.parent == Path("data") / "processed"
    assert res_empty.name.startswith("ui_run_")

    res_spaces = normalize_output_path("   ")
    assert res_spaces.parent == Path("data") / "processed"
    assert res_spaces.name.startswith("ui_run_")


def test_normalize_output_path_custom() -> None:
    """Test normalize_output_path returns custom path correctly."""
    res = normalize_output_path("  custom/output/dir  ")
    assert res == Path("custom/output/dir")
