"""Tests for the normalizer."""

from __future__ import annotations

import os
from pathlib import Path

from garmin_tcx_ai.models import (
    Activity,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
    WarningRecord,
)
from garmin_tcx_ai.normalizer import normalize_activity
from garmin_tcx_ai.parser import parse_tcx

FIXTURES = Path(__file__).parent / "fixtures"
MINIMAL_RUNNING = FIXTURES / "minimal_running.tcx"


def _make_activity() -> ParsedActivity:
    """Build a ParsedActivity with mixed present/missing values."""
    return ParsedActivity(
        source=SourceInfo(
            format="tcx",
            file_name=str(Path("data") / "raw" / "run.tcx"),
            file_path=str(Path("data") / "raw" / "run.tcx"),
        ),
        privacy=PrivacyInfo(gps_policy="keep"),
        activity=Activity(
            sport="Running",
            activity_id="id",
            distance_meters=None,
        ),
        trackpoints=[
            Trackpoint(
                trackpoint_index=1,
                lap_index=1,
                speed_mps=4.0,
                heart_rate_bpm=None,
            ),
            Trackpoint(
                trackpoint_index=2,
                lap_index=1,
                speed_mps=0.0,
            ),
        ],
        warnings=[
            WarningRecord(
                code="missing_optional_field",
                severity="warning",
                field="heart_rate_bpm",
                message="No HR.",
                source_file=str(Path("data") / "raw" / "run.tcx"),
            )
        ],
    )


def test_missing_values_stay_none() -> None:
    """Missing activity and trackpoint fields remain None."""
    result = normalize_activity(_make_activity(), "keep")
    assert result.activity.distance_meters is None
    assert result.trackpoints[0].heart_rate_bpm is None


def test_privacy_policy_recorded() -> None:
    """The requested gps_policy is recorded on the result."""
    result = normalize_activity(_make_activity(), "remove")
    assert result.privacy.gps_policy == "remove"


def test_source_file_name_is_bare_name() -> None:
    """source.file_name is reduced to a bare file name."""
    result = normalize_activity(_make_activity(), "keep")
    assert result.source.file_name == "run.tcx"
    assert os.sep not in result.source.file_name


def test_warning_source_file_has_no_path() -> None:
    """Warning source_file does not expose a directory component."""
    result = normalize_activity(_make_activity(), "keep")
    for w in result.warnings:
        assert os.sep not in w.source_file
        assert not Path(w.source_file).is_absolute()


def test_absolute_file_path_is_not_exposed() -> None:
    """An absolute source.file_path is reduced to a bare file name."""
    activity = _make_activity()
    activity.source.file_path = str(Path.cwd() / "data" / "raw" / "run.tcx")
    result = normalize_activity(activity, "keep")
    assert not Path(result.source.file_path).is_absolute()
    assert result.source.file_path == "run.tcx"


def test_relative_file_path_is_preserved() -> None:
    """A relative source.file_path is left untouched."""
    activity = _make_activity()
    activity.source.file_path = "data/raw/run.tcx"
    result = normalize_activity(activity, "keep")
    assert result.source.file_path == "data/raw/run.tcx"


def test_pace_derived_from_positive_speed() -> None:
    """pace_seconds_per_km is derived when speed_mps > 0, else None."""
    result = normalize_activity(_make_activity(), "keep")
    assert result.trackpoints[0].pace_seconds_per_km == 250.0
    assert result.trackpoints[1].pace_seconds_per_km is None


def test_input_not_mutated() -> None:
    """normalize_activity does not mutate its input."""
    original = _make_activity()
    normalize_activity(original, "remove")
    assert original.privacy.gps_policy == "keep"
    assert original.trackpoints[0].pace_seconds_per_km is None


def test_normalization_does_not_modify_fixture() -> None:
    """Normalizing parser output does not modify the raw fixture file."""
    mtime_before = MINIMAL_RUNNING.stat().st_mtime
    parsed = parse_tcx(MINIMAL_RUNNING)
    normalize_activity(parsed, "redact_start_end")
    mtime_after = MINIMAL_RUNNING.stat().st_mtime
    assert mtime_before == mtime_after
