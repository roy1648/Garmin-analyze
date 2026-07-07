"""Tests for the garmin-tcx-ai CLI entry point."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from garmin_tcx_ai.cli import main


def _has_gps_key(data: Any) -> bool:
    """Recursively check if a dictionary or list contains GPS-related keys."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ("latitude", "longitude"):
                return True
            if _has_gps_key(value):
                return True
    elif isinstance(data, list):
        for item in data:
            if _has_gps_key(item):
                return True
    return False


def test_cli_single_tcx_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI successfully processes a single valid TCX file."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0

    # Ensure output files exist
    bundle_json = output_dir / "session_bundle" / "session_bundle.json"
    bundle_md = output_dir / "session_bundle" / "session_bundle.md"
    assert bundle_json.is_file()
    assert bundle_md.is_file()

    # By default, atomic files are not written
    subdirs = [p.name for p in output_dir.iterdir() if p.is_dir()]
    assert subdirs == ["session_bundle"]

    # Verify stdout contains success summary and output path
    captured = capsys.readouterr()
    assert "Successfully processed 1 activities." in captured.out
    assert str(output_dir.resolve()) in captured.out


def test_cli_directory_success(tmp_path: Path) -> None:
    """CLI successfully processes all TCX files in a directory."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Copy only running TCX files to avoid parsing invalid/unsupported files
    shutil.copy(
        fixtures_dir / "minimal_running.tcx",
        input_dir / "minimal_running.tcx",
    )
    shutil.copy(
        fixtures_dir / "two_lap_running.tcx",
        input_dir / "two_lap_running.tcx",
    )

    output_dir = tmp_path / "output"

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "session_bundle" / "session_bundle.json").is_file()
    assert (output_dir / "session_bundle" / "session_bundle.md").is_file()


def test_cli_write_atomic(tmp_path: Path) -> None:
    """CLI writes atomic per-activity files when --write-atomic is set."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(output_dir),
            "--write-atomic",
        ]
    )

    assert exit_code == 0

    # Verify atomic directory and files exist
    activity_folder = output_dir / "2000-01-01T00_00_00Z"
    assert activity_folder.is_dir()
    assert (activity_folder / "activity.json").is_file()
    assert (activity_folder / "trackpoints.csv").is_file()
    assert (activity_folder / "ai_summary.json").is_file()
    assert (activity_folder / "ai_summary.md").is_file()


def test_cli_input_not_exists(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI fails when the input path does not exist."""
    exit_code = main(
        [
            "bundle",
            "--input",
            "non_existent_file.tcx",
            "--output",
            str(tmp_path),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error: Input path does not exist" in captured.err


def test_cli_directory_no_tcx(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI fails when the input directory has no .tcx files."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    exit_code = main(
        [
            "bundle",
            "--input",
            str(empty_dir),
            "--output",
            str(tmp_path),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error: No .tcx files found in directory" in captured.err


def test_cli_invalid_timezone(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI fails when an invalid timezone is provided."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(tmp_path),
            "--timezone",
            "Invalid/Timezone",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error: Invalid timezone name" in captured.err


def test_cli_negative_gap_minutes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI fails when a negative max gap is provided."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(tmp_path),
            "--max-gap-minutes",
            "-10",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error: max-gap-minutes must be greater than or equal to 0" in captured.err


def test_cli_session_bundle_safety(tmp_path: Path) -> None:
    """Session bundle excludes GPS coordinates and AI interpretations."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    bundle_json_path = output_dir / "session_bundle" / "session_bundle.json"

    with bundle_json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    # 1. No GPS coordinates (latitude / longitude keys)
    assert not _has_gps_key(data)

    # 2. Assert no Suggested Questions / coaching advice / medical interpretation
    policy = data["data_policy"]
    assert policy["no_workout_role_inference"] is True
    assert policy["no_coaching_advice"] is True
    assert policy["no_medical_interpretation"] is True

    # 3. Assert role inference is disabled
    for session in data["sessions"]:
        assert session["role_inference"] == "disabled"
        assert "suggested_questions" not in session
        assert "coaching_advice" not in session


def test_cli_directory_duplicate_activity_ids_no_overwrite(tmp_path: Path) -> None:
    """CLI avoids overwriting atomic files when duplicate activity IDs are found."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    # Both minimal_running and two_lap_running have the same activity ID 2000-01-01T00:00:00Z
    shutil.copy(
        fixtures_dir / "minimal_running.tcx",
        input_dir / "minimal_running.tcx",
    )
    shutil.copy(
        fixtures_dir / "two_lap_running.tcx",
        input_dir / "two_lap_running.tcx",
    )

    output_dir = tmp_path / "output"

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--write-atomic",
        ]
    )

    assert exit_code == 0

    # Ensure separate directories exist for each source file's atomic files
    min_run_folder = output_dir / "minimal_running" / "2000-01-01T00_00_00Z"
    two_lap_folder = output_dir / "two_lap_running" / "2000-01-01T00_00_00Z"

    assert min_run_folder.is_dir()
    assert (min_run_folder / "activity.json").is_file()
    assert (min_run_folder / "trackpoints.csv").is_file()

    assert two_lap_folder.is_dir()
    assert (two_lap_folder / "activity.json").is_file()
    assert (two_lap_folder / "trackpoints.csv").is_file()


def test_cli_without_coach_handoff(tmp_path: Path) -> None:
    """CLI by default does not write coach_handoff.md."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    bundle_json = output_dir / "session_bundle" / "session_bundle.json"
    bundle_md = output_dir / "session_bundle" / "session_bundle.md"
    handoff_md = output_dir / "session_bundle" / "coach_handoff.md"

    assert bundle_json.is_file()
    assert bundle_md.is_file()
    assert not handoff_md.exists()


def test_cli_with_coach_handoff(tmp_path: Path) -> None:
    """CLI writes coach_handoff.md when --write-coach-handoff is provided."""
    input_path = (
        Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    )
    output_dir = tmp_path / "output"

    exit_code = main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(output_dir),
            "--write-coach-handoff",
        ]
    )

    assert exit_code == 0
    bundle_json = output_dir / "session_bundle" / "session_bundle.json"
    bundle_md = output_dir / "session_bundle" / "session_bundle.md"
    handoff_md = output_dir / "session_bundle" / "coach_handoff.md"

    assert bundle_json.is_file()
    assert bundle_md.is_file()
    assert handoff_md.is_file()

    content = handoff_md.read_text(encoding="utf-8")
    assert "# TCX Coach Handoff" in content
    assert "這是多活動報告，每個 TCX 活動在報告中皆保持獨立紀錄。" in content
    assert "- Planned Workout:" in content
    assert "- RPE:" in content
    assert "- Pain Before / During / After:" in content
    assert "- Next Day Status:" in content
    assert "- Notes:" in content

    # Should contain core session bundle markdown content
    assert "# TCX Multi-Activity Report" in content

    # Safe check: no GPS or coaching/medical interpretation
    assert "latitude" not in content.lower()
    assert "longitude" not in content.lower()
    assert "suggested_questions" not in content.lower()
    assert "coaching_advice" not in content.lower()
    assert "medical_interpretation" not in content.lower()
    assert "Suggested Questions" not in content

