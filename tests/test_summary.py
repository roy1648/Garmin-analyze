"""Tests for factual no-inference activity summaries."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from garmin_tcx_ai.exporters import (
    write_ai_summary_json,
    write_ai_summary_markdown,
)
from garmin_tcx_ai.models import (
    Activity,
    Lap,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
    WarningRecord,
)
from garmin_tcx_ai.summary import build_ai_summary

START = datetime(2026, 5, 1, 6, 30, tzinfo=timezone.utc)
FORBIDDEN_LABELS = (
    "faster_later",
    "slower_later",
    "stable",
    "warmup",
    "cooldown",
    "interval",
    "tempo",
    "recovery",
    "long_run",
)


def _make_activity(
    trackpoints: list[Trackpoint] | None = None,
    laps: list[Lap] | None = None,
    activity: Activity | None = None,
    warnings: list[WarningRecord] | None = None,
    gps_policy: str = "keep",
) -> ParsedActivity:
    """Build a synthetic normalized activity."""
    if activity is None:
        activity = Activity(
            sport="Running",
            activity_id="2026-05-01T06:30:00Z",
            start_time=START,
            total_time_seconds=3600.0,
            distance_meters=10000.0,
            calories=650,
            average_heart_rate_bpm=145,
            maximum_heart_rate_bpm=172,
            maximum_speed_mps=4.2,
        )
    if laps is None:
        laps = [
            Lap(
                lap_index=1,
                start_time=START,
                total_time_seconds=1800.0,
                distance_meters=5000.0,
                average_heart_rate_bpm=142,
                maximum_heart_rate_bpm=168,
                maximum_speed_mps=4.1,
            ),
            Lap(
                lap_index=2,
                start_time=START + timedelta(seconds=1800),
                total_time_seconds=1800.0,
                distance_meters=5000.0,
                average_heart_rate_bpm=150,
                maximum_heart_rate_bpm=172,
                maximum_speed_mps=4.2,
            ),
        ]
    return ParsedActivity(
        source=SourceInfo("tcx", "run.tcx", "data/raw/run.tcx"),
        privacy=PrivacyInfo(gps_policy=gps_policy),
        activity=activity,
        laps=laps,
        trackpoints=trackpoints or [],
        warnings=warnings or [],
    )


def _split_trackpoints(
    first_pace: float = 360.0,
    second_pace: float = 390.0,
    first_hr: int | None = 150,
    second_hr: int | None = 160,
) -> list[Trackpoint]:
    """Build trackpoints spanning two fixed distance halves."""
    result = []
    elapsed = 0.0
    for index in range(11):
        distance = index * 1000.0
        if index:
            elapsed += first_pace if index <= 5 else second_pace
        result.append(
            Trackpoint(
                trackpoint_index=index + 1,
                timestamp=START + timedelta(seconds=elapsed),
                distance_meters=distance,
                heart_rate_bpm=(first_hr if index <= 5 else second_hr),
            )
        )
    return result


def test_top_level_schema_uses_neutral_policy_keys() -> None:
    """Summary replaces semantic trend/context keys with neutral data."""
    summary = build_ai_summary(_make_activity())
    assert tuple(summary) == (
        "activity_summary",
        "key_metrics",
        "lap_summary",
        "computed_split_metrics",
        "privacy",
        "data_quality",
        "data_policy",
    )
    assert "trend_summary" not in summary
    assert "ai_context" not in summary


def test_activity_and_key_metric_fixed_formulas() -> None:
    """Duration, distance, and pace use fixed arithmetic."""
    summary = build_ai_summary(_make_activity())
    assert summary["activity_summary"]["duration_minutes"] == 60.0
    assert summary["activity_summary"]["distance_km"] == 10.0
    assert summary["key_metrics"]["average_pace_seconds_per_km"] == 360.0
    assert summary["key_metrics"]["average_pace_formatted"] == "06:00/km"


def test_missing_activity_values_remain_none() -> None:
    """Missing values remain None and are never guessed."""
    summary = build_ai_summary(_make_activity(activity=Activity()))
    assert summary["activity_summary"]["start_time"] is None
    assert summary["key_metrics"]["average_pace_seconds_per_km"] is None


def test_lap_role_is_explicitly_not_inferred() -> None:
    """Every lap records the disabled role policy."""
    laps = build_ai_summary(_make_activity())["lap_summary"]
    assert laps
    assert all(lap["role"] is None for lap in laps)
    assert all(lap["role_source"] == "not_inferred" for lap in laps)


def test_computed_split_metrics_report_numeric_deltas() -> None:
    """Second-half deltas equal second half minus first half."""
    summary = build_ai_summary(
        _make_activity(trackpoints=_split_trackpoints())
    )
    split = summary["computed_split_metrics"]
    assert split["first_half_average_pace_seconds_per_km"] == 360.0
    assert split["second_half_average_pace_seconds_per_km"] == 390.0
    assert split["pace_second_half_delta_seconds_per_km"] == 30.0
    assert split["first_half_average_heart_rate_bpm"] == 150.0
    assert split["second_half_average_heart_rate_bpm"] == 160.0
    assert split["heart_rate_second_half_delta_bpm"] == 10.0
    assert split["pace_data_available"] is True
    assert split["heart_rate_data_available"] is True
    assert split["data_available"] is True


def test_computed_split_metrics_contain_no_semantic_labels() -> None:
    """Split output has numbers and policy, not interpretation labels."""
    split = build_ai_summary(
        _make_activity(trackpoints=_split_trackpoints())
    )["computed_split_metrics"]
    text = json.dumps(split).lower()
    for label in FORBIDDEN_LABELS:
        assert label not in text
    assert split["interpretation_policy"] == (
        "computed_metrics_only_no_training_interpretation"
    )


def test_split_metrics_missing_distance_are_unavailable() -> None:
    """Missing distance leaves split values unavailable with notes."""
    activity = Activity(total_time_seconds=600.0)
    summary = build_ai_summary(
        _make_activity(
            activity=activity,
            trackpoints=[Trackpoint(timestamp=START, heart_rate_bpm=140)],
        )
    )
    split = summary["computed_split_metrics"]
    assert split["data_available"] is False
    assert split["pace_second_half_delta_seconds_per_km"] is None
    assert split["heart_rate_second_half_delta_bpm"] is None
    assert any("Distance data" in note for note in split["notes"])


def test_split_availability_distinguishes_missing_heart_rate() -> None:
    """Available pace does not hide missing split heart-rate data."""
    split = build_ai_summary(
        _make_activity(
            trackpoints=_split_trackpoints(
                first_hr=None,
                second_hr=None,
            )
        )
    )["computed_split_metrics"]
    assert split["pace_data_available"] is True
    assert split["heart_rate_data_available"] is False
    assert split["data_available"] is False
    assert split["heart_rate_second_half_delta_bpm"] is None


def test_elevation_gain_records_computed_method() -> None:
    """Elevation gain identifies its fixed computation method."""
    points = [
        Trackpoint(altitude_meters=10.0),
        Trackpoint(altitude_meters=12.0),
        Trackpoint(altitude_meters=11.0),
        Trackpoint(altitude_meters=15.0),
    ]
    metrics = build_ai_summary(
        _make_activity(trackpoints=points)
    )["key_metrics"]
    assert metrics["estimated_elevation_gain_meters"] == 6.0
    assert metrics["estimated_elevation_gain_method"] == (
        "sum_positive_consecutive_altitude_deltas"
    )


def test_data_policy_records_no_inference() -> None:
    """Data policy explicitly disables all interpretation categories."""
    policy = build_ai_summary(_make_activity())["data_policy"]
    assert policy["source"] == "tcx_file"
    assert policy["no_workout_role_inference"] is True
    assert policy["no_coaching_advice"] is True
    assert policy["no_medical_interpretation"] is True


def test_summary_contains_no_coordinates_or_roles() -> None:
    """Summary omits GPS coordinates and prohibited role labels."""
    points = _split_trackpoints()
    for point in points:
        point.latitude = 23.456789
        point.longitude = 120.987654
    text = json.dumps(build_ai_summary(_make_activity(trackpoints=points)))
    lowered = text.lower()
    for value in ("latitude", "longitude", "23.456789", "120.987654"):
        assert value not in lowered
    for label in FORBIDDEN_LABELS:
        assert label not in lowered


def test_data_quality_counts_warnings_and_coverage() -> None:
    """Data quality reports warnings and factual coverage counts."""
    warnings = [
        WarningRecord(
            "missing_optional_field",
            "warning",
            "heart_rate_bpm",
            "Missing heart rate.",
            "run.tcx",
        )
    ]
    points = [Trackpoint(distance_meters=0.0), Trackpoint()]
    quality = build_ai_summary(
        _make_activity(trackpoints=points, warnings=warnings)
    )["data_quality"]
    assert quality["warnings_count"] == 1
    assert quality["warning_codes"] == ["missing_optional_field"]
    assert quality["trackpoints_count"] == 2
    assert quality["trackpoints_with_distance_count"] == 1


def test_markdown_removes_questions_and_semantic_output(tmp_path: Path) -> None:
    """Markdown contains facts and no active analysis prompts."""
    path = write_ai_summary_markdown(
        _make_activity(trackpoints=_split_trackpoints()), tmp_path
    )
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "Suggested AI Analysis Questions" not in text
    assert "## Computed Split Metrics" in text
    assert "## Data Policy" in text
    for label in FORBIDDEN_LABELS:
        assert label not in lowered
    for phrase in ("you should", "we recommend", "diagnosis"):
        assert phrase not in lowered


def test_json_and_markdown_exporters_match_policy(tmp_path: Path) -> None:
    """Single-activity exporters preserve the no-inference schema."""
    activity = _make_activity(trackpoints=_split_trackpoints())
    expected = build_ai_summary(activity)
    json_path = write_ai_summary_json(activity, tmp_path)
    md_path = write_ai_summary_markdown(activity, tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8")) == expected
    assert "redact_start_end" not in md_path.read_text(encoding="utf-8")
