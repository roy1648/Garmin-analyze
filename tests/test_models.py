"""Tests for the normalized Garmin TCX data models."""

from dataclasses import fields
from datetime import UTC, datetime

from garmin_tcx_ai.models import (
    Activity,
    Lap,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
    WarningRecord,
)


def test_models_accept_complete_contract_data() -> None:
    """All models accept the complete documented contract fields."""
    start_time = datetime(2026, 5, 1, 6, 30, tzinfo=UTC)
    source = SourceInfo(
        format="tcx",
        file_name="activity.tcx",
        file_path="data/raw/activity.tcx",
    )
    privacy = PrivacyInfo(gps_policy="redact_start_end")
    activity = Activity(
        sport="Running",
        activity_id="2026-05-01T06:30:00Z",
        start_time=start_time,
        total_time_seconds=3600.0,
        distance_meters=10000.0,
        calories=650,
        average_heart_rate_bpm=145,
        maximum_heart_rate_bpm=172,
        maximum_speed_mps=4.2,
    )
    lap = Lap(
        lap_index=1,
        start_time=start_time,
        total_time_seconds=1800.0,
        distance_meters=5000.0,
        calories=320,
        average_heart_rate_bpm=142,
        maximum_heart_rate_bpm=168,
        maximum_speed_mps=4.1,
        intensity="Active",
        trigger_method="Manual",
    )
    trackpoint = Trackpoint(
        trackpoint_index=1,
        lap_index=1,
        timestamp=start_time,
        latitude=25.0,
        longitude=121.0,
        altitude_meters=20.5,
        distance_meters=10.0,
        heart_rate_bpm=140,
        speed_mps=2.8,
        pace_seconds_per_km=357.1,
        run_cadence_spm=170,
        power_watts=230,
    )
    warning = WarningRecord(
        code="missing_optional_field",
        severity="warning",
        field="heart_rate_bpm",
        message="Heart rate is not available in the source file.",
        source_file="activity.tcx",
    )

    parsed = ParsedActivity(
        source=source,
        privacy=privacy,
        activity=activity,
        laps=[lap],
        trackpoints=[trackpoint],
        warnings=[warning],
    )

    assert parsed.source == source
    assert parsed.privacy == privacy
    assert parsed.activity == activity
    assert parsed.laps == [lap]
    assert parsed.trackpoints == [trackpoint]
    assert parsed.warnings == [warning]


def test_standard_activity_fields_default_to_none() -> None:
    """Optional standard fields default to None."""
    for model in (Activity(), Lap(), Trackpoint()):
        assert all(getattr(model, item.name) is None for item in fields(model))


def test_privacy_info_defaults_to_keep() -> None:
    """The default GPS privacy policy keeps coordinates."""
    assert PrivacyInfo().gps_policy == "keep"


def test_parsed_activity_collections_are_not_shared() -> None:
    """Each parsed activity owns independent mutable collections."""
    source = SourceInfo("tcx", "activity.tcx", "data/raw/activity.tcx")
    first = ParsedActivity(source, PrivacyInfo(), Activity())
    second = ParsedActivity(source, PrivacyInfo(), Activity())

    first.laps.append(Lap(lap_index=1))
    first.trackpoints.append(Trackpoint(trackpoint_index=1))
    first.warnings.append(
        WarningRecord(
            code="example",
            severity="info",
            field=None,
            message="Example warning.",
            source_file="activity.tcx",
        )
    )

    assert second.laps == []
    assert second.trackpoints == []
    assert second.warnings == []
