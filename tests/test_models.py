"""Tests for the normalized Garmin TCX data models."""

from garmin_tcx_ai.models import (
    Activity,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    WarningRecord,
)


def test_warning_record_fields() -> None:
    """Warning records expose every documented warning field."""
    warning = WarningRecord(
        code="missing_optional_field",
        severity="warning",
        field="heart_rate_bpm",
        message="Heart rate is not available in the source file.",
        source_file="activity.tcx",
    )

    assert warning.code == "missing_optional_field"
    assert warning.severity == "warning"
    assert warning.field == "heart_rate_bpm"
    assert warning.message == (
        "Heart rate is not available in the source file."
    )
    assert warning.source_file == "activity.tcx"


def test_warning_record_allows_file_level_warning() -> None:
    """A None field represents a warning for the entire source file."""
    warning = WarningRecord(
        code="unsupported_extension",
        severity="warning",
        field=None,
        message="An unsupported extension was ignored.",
        source_file="activity.tcx",
    )

    assert warning.field is None


def test_parsed_activity_allows_missing_optional_fields() -> None:
    """Parsed activities allow optional activity fields to be missing."""
    activity = Activity(
        activity_id=None,
        start_time=None,
        distance_meters=None,
        average_heart_rate_bpm=None,
        maximum_heart_rate_bpm=None,
        maximum_speed_mps=None,
    )
    parsed = ParsedActivity(
        source=SourceInfo("tcx", "activity.tcx", "data/raw/activity.tcx"),
        privacy=PrivacyInfo(),
        activity=activity,
    )

    assert parsed.activity.activity_id is None
    assert parsed.activity.start_time is None
    assert parsed.activity.distance_meters is None
    assert parsed.activity.average_heart_rate_bpm is None
    assert parsed.activity.maximum_heart_rate_bpm is None
    assert parsed.activity.maximum_speed_mps is None
    assert parsed.laps == []
    assert parsed.trackpoints == []
    assert parsed.warnings == []


def test_parsed_activity_list_fields_are_independent() -> None:
    """Each parsed activity owns independent mutable list fields."""
    source = SourceInfo("tcx", "activity.tcx", "data/raw/activity.tcx")
    first = ParsedActivity(source, PrivacyInfo(), Activity())
    second = ParsedActivity(source, PrivacyInfo(), Activity())

    first.warnings.append(
        WarningRecord(
            code="example",
            severity="info",
            field=None,
            message="Example warning.",
            source_file="activity.tcx",
        )
    )

    assert second.warnings == []
