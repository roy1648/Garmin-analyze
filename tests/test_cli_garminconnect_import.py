"""CLI tests for the optional Garmin Connect import command."""

from __future__ import annotations

from pathlib import Path

import pytest

import garmin_tcx_ai.cli as cli
from garmin_tcx_ai.importers import GarminConnectImportResult
from garmin_tcx_ai.pipeline import BundleRunResult


def test_import_garminconnect_success_runs_importer_then_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Successful import runs bundle processing on the download folder."""
    download_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    calls: list[object] = []

    def fake_import(config: object) -> GarminConnectImportResult:
        calls.append(config)
        return GarminConnectImportResult(
            success=True,
            downloaded_count=2,
            skipped_count=1,
            failed_count=0,
            download_dir=download_dir,
            tcx_paths=[download_dir / "a.tcx", download_dir / "b.tcx"],
            warning_messages=["import warning"],
        )

    def fake_bundle(config: object) -> BundleRunResult:
        calls.append(config)
        assert getattr(config, "input_path") == download_dir
        assert getattr(config, "output_dir") == output_dir
        return BundleRunResult(
            success=True,
            activity_count=2,
            output_dir=output_dir,
            warning_messages=["pipeline warning"],
        )

    monkeypatch.setattr(cli, "download_tcx_activities", fake_import)
    monkeypatch.setattr(cli, "run_bundle", fake_bundle)

    exit_code = cli.main(
        [
            "import-garminconnect",
            "--start-date",
            "2026-07-01",
            "--end-date",
            "2026-07-08",
            "--activity-type",
            "running",
            "--download-dir",
            str(download_dir),
            "--email",
            "runner@example.test",
            "--output",
            str(output_dir),
            "--gps-policy",
            "redact_start_end",
            "--timezone",
            "Asia/Taipei",
            "--max-gap-minutes",
            "30",
            "--write-coach-handoff",
        ]
    )

    assert exit_code == 0
    assert len(calls) == 2
    captured = capsys.readouterr()
    assert "import warning" in captured.err
    assert "pipeline warning" in captured.err
    assert "Downloaded activities: 2" in captured.out
    assert "Skipped activities: 1" in captured.out
    assert "Failed activities: 0" in captured.out
    assert "Processed activities: 2" in captured.out


def test_import_garminconnect_importer_failure_skips_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Importer failure returns exit code 1 without running pipeline."""
    def fake_import(config: object) -> GarminConnectImportResult:
        return GarminConnectImportResult(
            success=False,
            downloaded_count=0,
            skipped_count=0,
            failed_count=0,
            download_dir=tmp_path / "raw",
            tcx_paths=[],
            warning_messages=["import warning"],
            error_message="import failed",
        )

    def fake_bundle(config: object) -> BundleRunResult:
        raise AssertionError("run_bundle should not be called")

    monkeypatch.setattr(cli, "download_tcx_activities", fake_import)
    monkeypatch.setattr(cli, "run_bundle", fake_bundle)

    exit_code = cli.main(
        [
            "import-garminconnect",
            "--start-date",
            "2026-07-01",
            "--end-date",
            "2026-07-08",
            "--output",
            str(tmp_path / "processed"),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "import warning" in captured.err
    assert "import failed" in captured.err


def test_import_garminconnect_pipeline_failure_returns_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pipeline failure after import returns exit code 1."""
    def fake_import(config: object) -> GarminConnectImportResult:
        return GarminConnectImportResult(
            success=True,
            downloaded_count=1,
            skipped_count=0,
            failed_count=0,
            download_dir=tmp_path / "raw",
            tcx_paths=[tmp_path / "raw" / "a.tcx"],
            warning_messages=[],
        )

    def fake_bundle(config: object) -> BundleRunResult:
        return BundleRunResult(
            success=False,
            activity_count=0,
            output_dir=tmp_path / "processed",
            warning_messages=["pipeline warning"],
            error_message="pipeline failed",
        )

    monkeypatch.setattr(cli, "download_tcx_activities", fake_import)
    monkeypatch.setattr(cli, "run_bundle", fake_bundle)

    exit_code = cli.main(
        [
            "import-garminconnect",
            "--start-date",
            "2026-07-01",
            "--end-date",
            "2026-07-08",
            "--output",
            str(tmp_path / "processed"),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "pipeline warning" in captured.err
    assert "pipeline failed" in captured.err


def test_existing_bundle_command_still_works(tmp_path: Path) -> None:
    """The original bundle command remains available."""
    input_path = Path(__file__).parent / "fixtures" / "minimal_running.tcx"
    output_dir = tmp_path / "output"

    exit_code = cli.main(
        [
            "bundle",
            "--input",
            str(input_path),
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "session_bundle" / "session_bundle.json").is_file()
