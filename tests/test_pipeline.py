"""Unit tests for the shared pipeline module."""

from __future__ import annotations

import shutil
from pathlib import Path

from garmin_tcx_ai.pipeline import BundleRunConfig, run_bundle


def test_run_bundle_single_tcx_success(tmp_path: Path) -> None:
    """run_bundle successfully processes a single valid TCX file."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    config = BundleRunConfig(
        input_path=input_path,
        output_dir=output_dir,
    )
    result = run_bundle(config)

    assert result.success is True
    assert result.activity_count == 1
    assert result.error_message is None
    assert result.session_bundle_json_path is not None
    assert result.session_bundle_json_path.is_file()
    assert result.session_bundle_markdown_path is not None
    assert result.session_bundle_markdown_path.is_file()
    assert result.coach_handoff_markdown_path is None
    assert not result.atomic_artifact_paths


def test_run_bundle_missing_input_returns_error(tmp_path: Path) -> None:
    """run_bundle returns success=False when input path does not exist."""
    input_path = Path("non_existent_file.tcx")
    output_dir = tmp_path / "output"

    config = BundleRunConfig(
        input_path=input_path,
        output_dir=output_dir,
    )
    result = run_bundle(config)

    assert result.success is False
    assert result.activity_count == 0
    assert result.error_message is not None
    assert "Input path does not exist" in result.error_message


def test_run_bundle_directory_keeps_warnings_for_invalid_files(
    tmp_path: Path,
) -> None:
    """run_bundle records warnings and continues in directory mode."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Copy one valid running TCX and one invalid TCX
    shutil.copy(
        fixtures_dir / "minimal_running.tcx",
        input_dir / "minimal_running.tcx",
    )
    shutil.copy(
        fixtures_dir / "invalid.tcx",
        input_dir / "invalid.tcx",
    )

    output_dir = tmp_path / "output"
    config = BundleRunConfig(
        input_path=input_dir,
        output_dir=output_dir,
    )
    result = run_bundle(config)

    assert result.success is True
    assert result.activity_count == 1
    assert len(result.warning_messages) > 0
    # Warning message should mention invalid.tcx
    assert any("invalid.tcx" in msg for msg in result.warning_messages)
    assert result.session_bundle_json_path is not None
    assert result.session_bundle_json_path.is_file()


def test_run_bundle_with_coach_handoff_returns_path(tmp_path: Path) -> None:
    """run_bundle returns the coach handoff markdown path when requested."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    config = BundleRunConfig(
        input_path=input_path,
        output_dir=output_dir,
        write_coach_handoff=True,
    )
    result = run_bundle(config)

    assert result.success is True
    assert result.coach_handoff_markdown_path is not None
    assert result.coach_handoff_markdown_path.is_file()


def test_run_bundle_write_atomic_returns_artifact_paths(
    tmp_path: Path,
) -> None:
    """run_bundle generates and returns atomic artifact paths when requested."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    config = BundleRunConfig(
        input_path=input_path,
        output_dir=output_dir,
        write_atomic=True,
    )
    result = run_bundle(config)

    assert result.success is True
    assert len(result.atomic_artifact_paths) > 0
    for path in result.atomic_artifact_paths:
        assert path.is_file()
