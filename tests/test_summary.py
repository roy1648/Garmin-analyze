"""Tests for the AI summary builder."""

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

START = datetime(2026, 5, 1, 6, 30, 0, tzinfo=timezone.utc)

TOP_LEVEL_KEYS = (
    "activity_summary",
    "key_metrics",
    "lap_summary",
    "trend_summary",
    "privacy",
    "data_quality",
    "ai_context",
)

ACTIVITY_SUMMARY_KEYS = (
    "sport",
    "activity_id",
    "start_time",
    "duration_minutes",
    "distance_km",
    "lap_count",
    "trackpoint_count",
)

KEY_METRICS_KEYS = (
    "duration_minutes",
    "distance_km",
    "average_pace_seconds_per_km",
    "average_pace_formatted",
    "average_heart_rate_bpm",
    "maximum_heart_rate_bpm",
    "maximum_speed_mps",
    "min_altitude_meters",
    "max_altitude_meters",
    "estimated_elevation_gain_meters",
    "lap_count",
)

LAP_KEYS = (
    "lap_index",
    "start_time",
    "duration_minutes",
    "distance_km",
    "average_pace_seconds_per_km",
    "average_pace_formatted",
    "average_heart_rate_bpm",
    "maximum_heart_rate_bpm",
    "maximum_speed_mps",
)

TREND_KEYS = (
    "pace_trend",
    "heart_rate_trend",
    "first_half_average_pace_seconds_per_km",
    "second_half_average_pace_seconds_per_km",
    "first_half_average_heart_rate_bpm",
    "second_half_average_heart_rate_bpm",
    "method",
    "notes",
)

DATA_QUALITY_KEYS = (
    "warnings_count",
    "warning_codes",
    "missing_key_fields",
    "trackpoints_count",
    "trackpoints_with_gps_count",
    "trackpoints_with_heart_rate_count",
    "trackpoints_with_distance_count",
    "trackpoints_with_speed_count",
    "trackpoints_with_altitude_count",
    "notes",
)


def _make_activity(
    trackpoints: list[Trackpoint] | None = None,
    laps: list[Lap] | None = None,
    activity: Activity | None = None,
    warnings: list[WarningRecord] | None = None,
    gps_policy: str = "keep",
) -> ParsedActivity:
    """Build a synthetic normalized-looking ParsedActivity."""
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
        source=SourceInfo(
            format="tcx",
            file_name="run.tcx",
            file_path="data/raw/run.tcx",
        ),
        privacy=PrivacyInfo(gps_policy=gps_policy),
        activity=activity,
        laps=laps,
        trackpoints=trackpoints if trackpoints is not None else [],
        warnings=warnings if warnings is not None else [],
    )


def _trend_trackpoints(
    first_pace: float,
    second_pace: float,
    first_hr: int | None = 145,
    second_hr: int | None = 150,
) -> list[Trackpoint]:
    """Build 11 trackpoints over 10 km with per-half pace and HR.

    Points sit every 1000 m from 0 to 10000. Each kilometer up to the
    5000 m midpoint takes *first_pace* seconds; later kilometers take
    *second_pace* seconds. HR readings follow the same split.
    """
    points: list[Trackpoint] = []
    elapsed = 0.0
    for i in range(11):
        distance = i * 1000.0
        if i > 0:
            pace = first_pace if distance <= 5000.0 else second_pace
            elapsed += pace
        hr = first_hr if distance <= 5000.0 else second_hr
        points.append(
            Trackpoint(
                trackpoint_index=i + 1,
                lap_index=1,
                timestamp=START + timedelta(seconds=elapsed),
                distance_meters=distance,
                heart_rate_bpm=hr,
            )
        )
    return points


# --- structure ---------------------------------------------------------


def test_top_level_keys_complete() -> None:
    """The summary contains every required top-level key."""
    summary = build_ai_summary(_make_activity())
    assert tuple(summary.keys()) == TOP_LEVEL_KEYS


def test_activity_summary_fields_complete() -> None:
    """activity_summary contains all required fields."""
    summary = build_ai_summary(_make_activity())
    for key in ACTIVITY_SUMMARY_KEYS:
        assert key in summary["activity_summary"]


def test_key_metrics_fields_complete() -> None:
    """key_metrics contains all required fields."""
    summary = build_ai_summary(_make_activity())
    for key in KEY_METRICS_KEYS:
        assert key in summary["key_metrics"]


def test_trend_summary_fields_complete() -> None:
    """trend_summary contains all required fields."""
    summary = build_ai_summary(_make_activity())
    for key in TREND_KEYS:
        assert key in summary["trend_summary"]


def test_data_quality_fields_complete() -> None:
    """data_quality contains all required fields."""
    summary = build_ai_summary(_make_activity())
    for key in DATA_QUALITY_KEYS:
        assert key in summary["data_quality"]


# --- activity_summary / key_metrics ------------------------------------


def test_missing_activity_fields_are_none() -> None:
    """Missing activity values become None, never guesses."""
    empty = _make_activity(activity=Activity())
    summary = build_ai_summary(empty)
    act = summary["activity_summary"]
    assert act["sport"] is None
    assert act["activity_id"] is None
    assert act["start_time"] is None
    assert act["duration_minutes"] is None
    assert act["distance_km"] is None
    metrics = summary["key_metrics"]
    assert metrics["average_pace_seconds_per_km"] is None
    assert metrics["average_pace_formatted"] is None
    assert metrics["average_heart_rate_bpm"] is None


def test_duration_and_distance_conversion() -> None:
    """duration_minutes and distance_km follow the contract math."""
    summary = build_ai_summary(_make_activity())
    act = summary["activity_summary"]
    assert act["duration_minutes"] == 60.0
    assert act["distance_km"] == 10.0
    assert act["lap_count"] == 2
    assert act["start_time"] == "2026-05-01T06:30:00Z"


def test_average_pace_seconds_calculation() -> None:
    """Average pace is total_time / distance_km."""
    summary = build_ai_summary(_make_activity())
    metrics = summary["key_metrics"]
    assert metrics["average_pace_seconds_per_km"] == 360.0
    assert metrics["average_pace_formatted"] == "06:00/km"


def test_average_pace_formatted_rounds_to_second() -> None:
    """357.1 s/km formats as 05:57/km."""
    activity = Activity(
        total_time_seconds=3571.0,
        distance_meters=10000.0,
    )
    summary = build_ai_summary(_make_activity(activity=activity))
    metrics = summary["key_metrics"]
    assert metrics["average_pace_seconds_per_km"] == 357.1
    assert metrics["average_pace_formatted"] == "05:57/km"


def test_average_pace_none_when_zero_distance() -> None:
    """Zero or missing distance yields a None pace."""
    activity = Activity(
        total_time_seconds=3600.0,
        distance_meters=0.0,
    )
    summary = build_ai_summary(_make_activity(activity=activity))
    assert summary["key_metrics"]["average_pace_seconds_per_km"] is None


# --- lap_summary --------------------------------------------------------


def test_lap_summary_entries() -> None:
    """Each lap produces a complete summary entry."""
    summary = build_ai_summary(_make_activity())
    laps = summary["lap_summary"]
    assert len(laps) == 2
    for key in LAP_KEYS:
        assert key in laps[0]
    assert laps[0]["lap_index"] == 1
    assert laps[1]["lap_index"] == 2
    assert laps[0]["duration_minutes"] == 30.0
    assert laps[0]["distance_km"] == 5.0


def test_lap_pace_uses_lap_values() -> None:
    """Lap pace is computed from the lap's own time and distance."""
    summary = build_ai_summary(_make_activity())
    lap = summary["lap_summary"][0]
    assert lap["average_pace_seconds_per_km"] == 360.0
    assert lap["average_pace_formatted"] == "06:00/km"


def test_lap_missing_values_are_none() -> None:
    """Laps with missing values report None."""
    summary = build_ai_summary(_make_activity(laps=[Lap(lap_index=1)]))
    lap = summary["lap_summary"][0]
    assert lap["average_pace_seconds_per_km"] is None
    assert lap["average_heart_rate_bpm"] is None


# --- elevation ----------------------------------------------------------


def test_min_max_altitude() -> None:
    """Min/max altitude use only non-None readings."""
    points = [
        Trackpoint(altitude_meters=10.0),
        Trackpoint(altitude_meters=None),
        Trackpoint(altitude_meters=15.0),
        Trackpoint(altitude_meters=12.0),
    ]
    summary = build_ai_summary(_make_activity(trackpoints=points))
    metrics = summary["key_metrics"]
    assert metrics["min_altitude_meters"] == 10.0
    assert metrics["max_altitude_meters"] == 15.0


def test_elevation_gain_sums_positive_deltas_only() -> None:
    """Elevation gain adds only positive climbs: +2 and +4 here."""
    points = [
        Trackpoint(altitude_meters=10.0),
        Trackpoint(altitude_meters=12.0),
        Trackpoint(altitude_meters=11.0),
        Trackpoint(altitude_meters=15.0),
    ]
    summary = build_ai_summary(_make_activity(trackpoints=points))
    gain = summary["key_metrics"]["estimated_elevation_gain_meters"]
    assert gain == 6.0


def test_elevation_gain_none_with_insufficient_data() -> None:
    """Fewer than two altitude readings yield a None gain."""
    points = [Trackpoint(altitude_meters=10.0), Trackpoint()]
    summary = build_ai_summary(_make_activity(trackpoints=points))
    metrics = summary["key_metrics"]
    assert metrics["estimated_elevation_gain_meters"] is None
    assert metrics["min_altitude_meters"] == 10.0


# --- trend_summary -------------------------------------------------------


def test_trend_midpoint_split_paces() -> None:
    """Halves are split at the distance midpoint with correct paces."""
    points = _trend_trackpoints(first_pace=360.0, second_pace=300.0)
    summary = build_ai_summary(_make_activity(trackpoints=points))
    trend = summary["trend_summary"]
    first = trend["first_half_average_pace_seconds_per_km"]
    second = trend["second_half_average_pace_seconds_per_km"]
    assert first == 360.0
    assert second == 300.0


def test_pace_trend_faster_later() -> None:
    """A >3% faster second half is labeled faster_later."""
    points = _trend_trackpoints(first_pace=360.0, second_pace=300.0)
    summary = build_ai_summary(_make_activity(trackpoints=points))
    assert summary["trend_summary"]["pace_trend"] == "faster_later"


def test_pace_trend_slower_later() -> None:
    """A >3% slower second half is labeled slower_later."""
    points = _trend_trackpoints(first_pace=300.0, second_pace=360.0)
    summary = build_ai_summary(_make_activity(trackpoints=points))
    assert summary["trend_summary"]["pace_trend"] == "slower_later"


def test_pace_trend_stable() -> None:
    """Pace changes within 3% are labeled stable."""
    points = _trend_trackpoints(first_pace=360.0, second_pace=365.0)
    summary = build_ai_summary(_make_activity(trackpoints=points))
    assert summary["trend_summary"]["pace_trend"] == "stable"


def test_pace_trend_insufficient_without_timestamps() -> None:
    """Missing timestamps yield insufficient_data pace trend."""
    points = _trend_trackpoints(first_pace=360.0, second_pace=300.0)
    for tp in points:
        tp.timestamp = None
    summary = build_ai_summary(_make_activity(trackpoints=points))
    trend = summary["trend_summary"]
    assert trend["pace_trend"] == "insufficient_data"
    assert trend["first_half_average_pace_seconds_per_km"] is None


def test_pace_trend_sparse_boundary_sample_included() -> None:
    """The midpoint sample is shared so a sparse 3-point run still
    computes a second-half pace instead of insufficient_data."""
    points = [
        Trackpoint(
            timestamp=START, distance_meters=0.0, heart_rate_bpm=140,
        ),
        Trackpoint(
            timestamp=START + timedelta(seconds=1800),
            distance_meters=5000.0,
            heart_rate_bpm=150,
        ),
        Trackpoint(
            timestamp=START + timedelta(seconds=3300),
            distance_meters=10000.0,
            heart_rate_bpm=160,
        ),
    ]
    summary = build_ai_summary(_make_activity(trackpoints=points))
    trend = summary["trend_summary"]
    assert trend["second_half_average_pace_seconds_per_km"] is not None
    assert trend["pace_trend"] != "insufficient_data"


def test_trends_insufficient_without_distance() -> None:
    """No distance anywhere yields insufficient_data for both trends."""
    activity = Activity(total_time_seconds=3600.0)
    points = [
        Trackpoint(timestamp=START, heart_rate_bpm=140),
        Trackpoint(
            timestamp=START + timedelta(seconds=600),
            heart_rate_bpm=150,
        ),
    ]
    summary = build_ai_summary(
        _make_activity(trackpoints=points, activity=activity)
    )
    trend = summary["trend_summary"]
    assert trend["pace_trend"] == "insufficient_data"
    assert trend["heart_rate_trend"] == "insufficient_data"
    assert trend["notes"]


def test_heart_rate_trend_slower_later() -> None:
    """A >3% higher second-half HR is labeled slower_later."""
    points = _trend_trackpoints(
        first_pace=360.0, second_pace=360.0,
        first_hr=140, second_hr=160,
    )
    summary = build_ai_summary(_make_activity(trackpoints=points))
    trend = summary["trend_summary"]
    assert trend["heart_rate_trend"] == "slower_later"
    assert trend["first_half_average_heart_rate_bpm"] == 140.0
    assert trend["second_half_average_heart_rate_bpm"] == 160.0


def test_heart_rate_trend_faster_later() -> None:
    """A >3% lower second-half HR is labeled faster_later."""
    points = _trend_trackpoints(
        first_pace=360.0, second_pace=360.0,
        first_hr=160, second_hr=140,
    )
    summary = build_ai_summary(_make_activity(trackpoints=points))
    assert (
        summary["trend_summary"]["heart_rate_trend"] == "faster_later"
    )


def test_heart_rate_trend_stable() -> None:
    """HR changes within 3% are labeled stable."""
    points = _trend_trackpoints(
        first_pace=360.0, second_pace=360.0,
        first_hr=145, second_hr=147,
    )
    summary = build_ai_summary(_make_activity(trackpoints=points))
    assert summary["trend_summary"]["heart_rate_trend"] == "stable"


def test_heart_rate_trend_insufficient_without_hr() -> None:
    """Missing HR in one half yields insufficient_data HR trend."""
    points = _trend_trackpoints(
        first_pace=360.0, second_pace=360.0,
        first_hr=145, second_hr=None,
    )
    summary = build_ai_summary(_make_activity(trackpoints=points))
    trend = summary["trend_summary"]
    assert trend["heart_rate_trend"] == "insufficient_data"
    assert trend["second_half_average_heart_rate_bpm"] is None


def test_trend_method_mentions_rules() -> None:
    """The method field records midpoint split and 3% threshold."""
    summary = build_ai_summary(_make_activity())
    method = summary["trend_summary"]["method"]
    assert "midpoint" in method
    assert "3%" in method
    assert "insufficient_data" in method


# --- privacy -------------------------------------------------------------


def test_privacy_reports_gps_policy() -> None:
    """privacy carries the activity gps_policy and fixed flags."""
    parsed = _make_activity(gps_policy="redact_start_end")
    summary = build_ai_summary(parsed)
    privacy = summary["privacy"]
    assert privacy["gps_policy"] == "redact_start_end"
    assert privacy["gps_included_in_summary"] is False
    assert privacy["route_details_included"] is False


def test_summary_contains_no_coordinates() -> None:
    """Raw latitude/longitude never appear anywhere in the summary."""
    points = _trend_trackpoints(first_pace=360.0, second_pace=360.0)
    for tp in points:
        tp.latitude = 23.456789
        tp.longitude = 120.987654
    summary = build_ai_summary(_make_activity(trackpoints=points))
    text = json.dumps(summary)
    assert "latitude" not in text
    assert "longitude" not in text
    assert "23.456789" not in text
    assert "120.987654" not in text


# --- data_quality ----------------------------------------------------------


def test_data_quality_counts_warnings() -> None:
    """warnings_count and warning_codes reflect the warning list."""
    warnings = [
        WarningRecord(
            code="missing_optional_field",
            severity="warning",
            field="heart_rate_bpm",
            message="No HR.",
            source_file="run.tcx",
        ),
        WarningRecord(
            code="missing_optional_field",
            severity="warning",
            field="altitude_meters",
            message="No altitude.",
            source_file="run.tcx",
        ),
        WarningRecord(
            code="skipped_extension",
            severity="info",
            field=None,
            message="Skipped.",
            source_file="run.tcx",
        ),
    ]
    summary = build_ai_summary(_make_activity(warnings=warnings))
    quality = summary["data_quality"]
    assert quality["warnings_count"] == 3
    assert quality["warning_codes"] == [
        "missing_optional_field",
        "skipped_extension",
    ]


def test_data_quality_trackpoint_coverage() -> None:
    """Per-field trackpoint coverage counts are correct."""
    points = [
        Trackpoint(
            timestamp=START,
            latitude=23.5,
            longitude=121.0,
            distance_meters=0.0,
            heart_rate_bpm=140,
            speed_mps=2.8,
            altitude_meters=10.0,
        ),
        Trackpoint(
            timestamp=START + timedelta(seconds=10),
            distance_meters=30.0,
            heart_rate_bpm=None,
            speed_mps=None,
            altitude_meters=None,
        ),
        Trackpoint(),
    ]
    summary = build_ai_summary(_make_activity(trackpoints=points))
    quality = summary["data_quality"]
    assert quality["trackpoints_count"] == 3
    assert quality["trackpoints_with_gps_count"] == 1
    assert quality["trackpoints_with_heart_rate_count"] == 1
    assert quality["trackpoints_with_distance_count"] == 2
    assert quality["trackpoints_with_speed_count"] == 1
    assert quality["trackpoints_with_altitude_count"] == 1


def test_missing_key_fields_listed() -> None:
    """Missing activity and trackpoint fields are listed explicitly."""
    parsed = _make_activity(activity=Activity(), trackpoints=[])
    summary = build_ai_summary(parsed)
    missing = summary["data_quality"]["missing_key_fields"]
    for name in (
        "activity.start_time",
        "activity.total_time_seconds",
        "activity.distance_meters",
        "activity.average_heart_rate_bpm",
        "activity.maximum_heart_rate_bpm",
        "trackpoints.timestamp",
        "trackpoints.distance_meters",
        "trackpoints.heart_rate_bpm",
        "trackpoints.altitude_meters",
        "trackpoints.speed_mps",
    ):
        assert name in missing


def test_missing_key_fields_empty_when_complete() -> None:
    """A fully populated activity reports no missing key fields."""
    points = _trend_trackpoints(first_pace=360.0, second_pace=360.0)
    for tp in points:
        tp.altitude_meters = 10.0
        tp.speed_mps = 2.8
    summary = build_ai_summary(_make_activity(trackpoints=points))
    assert summary["data_quality"]["missing_key_fields"] == []


# --- ai_context ------------------------------------------------------------


def test_ai_context_is_factual_text() -> None:
    """ai_context states its factual purpose without advice."""
    summary = build_ai_summary(_make_activity())
    context = summary["ai_context"]
    assert isinstance(context, str)
    assert "factual summary" in context
    assert "no coaching advice" in context
    assert "no medical interpretation" in context


# --- integration -------------------------------------------------------------


def test_full_pipeline_files_consistent(tmp_path: Path) -> None:
    """Both exporters write readable files consistent with the dict."""
    points = _trend_trackpoints(first_pace=360.0, second_pace=300.0)
    for tp in points:
        tp.latitude = 23.456789
        tp.longitude = 120.987654
    parsed = _make_activity(
        trackpoints=points, gps_policy="redact_start_end"
    )

    summary = build_ai_summary(parsed)
    json_path = write_ai_summary_json(parsed, tmp_path)
    md_path = write_ai_summary_markdown(parsed, tmp_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data == json.loads(json.dumps(summary))
    assert data["trend_summary"]["pace_trend"] == "faster_later"

    markdown = md_path.read_text(encoding="utf-8")
    assert "faster_later" in markdown
    assert "redact_start_end" in markdown
    for text in (json.dumps(data), markdown):
        assert "23.456789" not in text
        assert "120.987654" not in text
        assert "latitude" not in text.lower()
