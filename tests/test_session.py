"""Tests for multi-TCX no-inference session bundles."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from garmin_tcx_ai.models import (
    Activity,
    Lap,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
)
from garmin_tcx_ai.session import (
    build_session_bundle,
    render_session_bundle_markdown,
)

START = datetime(2026, 7, 5, 6, 0, tzinfo=timezone.utc)
TOP_LEVEL_KEYS = {
    "schema_version",
    "export_scope",
    "data_policy",
    "sessions",
    "data_quality",
    "privacy",
}
PROHIBITED_ROLES = (
    "warmup",
    "cooldown",
    "tempo",
    "recovery",
    "long_run",
    "long run",
    "quality_session",
    "quality session",
    "main set",
    "collapse",
)
MISLEADING_REPORT_WORDING = (
    "merged workout",
    "merged session",
    "combined workout",
    "合併成一堂訓練",
    "合併成一堂課",
)


def _activity(
    name: str,
    start: datetime | None,
    *,
    sport: str = "Running",
    distance_meters: float | None = 5000.0,
    duration_seconds: float | None = 600.0,
    average_hr: int | None = 150,
    maximum_hr: int | None = 170,
    run_cadence: int | None = None,
    power: int | None = None,
) -> ParsedActivity:
    """Build one synthetic normalized activity."""
    trackpoint = Trackpoint(
        timestamp=start,
        latitude=23.456789,
        longitude=120.987654,
        distance_meters=0.0,
        heart_rate_bpm=average_hr,
        run_cadence_spm=run_cadence,
        power_watts=power,
    )
    return ParsedActivity(
        source=SourceInfo("tcx", name, f"data/raw/{name}"),
        privacy=PrivacyInfo("redact_start_end"),
        activity=Activity(
            sport=sport,
            activity_id=start.isoformat() if start else name,
            start_time=start,
            total_time_seconds=duration_seconds,
            distance_meters=distance_meters,
            average_heart_rate_bpm=average_hr,
            maximum_heart_rate_bpm=maximum_hr,
        ),
        laps=[
            Lap(
                lap_index=1,
                start_time=start,
                total_time_seconds=duration_seconds,
                distance_meters=distance_meters,
                average_heart_rate_bpm=average_hr,
                maximum_heart_rate_bpm=maximum_hr,
            )
        ],
        trackpoints=[trackpoint],
    )


def test_bundle_top_level_and_data_policy_are_complete() -> None:
    """Bundle exposes the required schema and policy keys."""
    bundle = build_session_bundle([_activity("one.tcx", START)])
    assert set(bundle) == TOP_LEVEL_KEYS
    assert bundle["schema_version"] == "tcx_training_data_v1"
    assert bundle["export_scope"] == {
        "type": "session_bundle",
        "activity_count": 1,
        "session_candidate_count": 1,
        "contains_multiple_activities": False,
    }
    policy = bundle["data_policy"]
    assert policy["activity_equals_one_tcx_file"] is True
    assert policy["session_may_contain_multiple_activities"] is True
    assert policy["grouping_is_candidate_not_fact"] is True
    assert policy["no_workout_role_inference"] is True
    assert policy["no_coaching_advice"] is True
    assert policy["no_medical_interpretation"] is True
    assert policy["manual_context_fields_are_placeholders"] is True


def test_activities_are_sorted_and_grouped_within_gap() -> None:
    """Same-date same-sport activities within 30 minutes form one candidate."""
    later = _activity("later.tcx", START + timedelta(minutes=25))
    earlier = _activity("earlier.tcx", START)
    bundle = build_session_bundle([later, earlier])
    assert bundle["export_scope"]["session_candidate_count"] == 1
    session = bundle["sessions"][0]
    assert session["grouping_confidence"] == "candidate"
    assert session["role_inference"] == "disabled"
    assert [item["source_file"] for item in session["activities"]] == [
        "earlier.tcx",
        "later.tcx",
    ]
    assert [item["activity_order"] for item in session["activities"]] == [
        1,
        2,
    ]
    assert bundle["export_scope"]["contains_multiple_activities"] is True


def test_gap_over_limit_creates_separate_candidates() -> None:
    """An adjacent start-time gap over the limit starts a new candidate."""
    bundle = build_session_bundle(
        [
            _activity("one.tcx", START),
            _activity("two.tcx", START + timedelta(minutes=31)),
        ]
    )
    assert len(bundle["sessions"]) == 2


def test_gap_equal_to_limit_stays_in_one_candidate() -> None:
    """A start-time gap equal to the limit remains in one candidate."""
    bundle = build_session_bundle(
        [
            _activity("one.tcx", START),
            _activity("two.tcx", START + timedelta(minutes=30)),
        ]
    )
    assert len(bundle["sessions"]) == 1


def test_different_sport_creates_separate_candidates() -> None:
    """Different sports never share a session candidate."""
    bundle = build_session_bundle(
        [
            _activity("run.tcx", START),
            _activity(
                "ride.tcx", START + timedelta(minutes=5), sport="Cycling"
            ),
        ]
    )
    assert len(bundle["sessions"]) == 2


def test_different_local_date_creates_separate_candidates() -> None:
    """Activities with different configured local dates remain separate."""
    bundle = build_session_bundle(
        [
            _activity("one.tcx", START),
            _activity("two.tcx", START + timedelta(days=1)),
        ]
    )
    assert len(bundle["sessions"]) == 2


def test_grouping_uses_configured_local_date() -> None:
    """Local date is derived by deterministic timezone conversion."""
    first = datetime(2026, 7, 5, 15, 50, tzinfo=timezone.utc)
    second = datetime(2026, 7, 5, 16, 10, tzinfo=timezone.utc)
    taipei = build_session_bundle(
        [_activity("one.tcx", first), _activity("two.tcx", second)],
        timezone_name="Asia/Taipei",
    )
    utc = build_session_bundle(
        [_activity("one.tcx", first), _activity("two.tcx", second)],
        timezone_name="UTC",
    )
    assert len(taipei["sessions"]) == 2
    assert len(utc["sessions"]) == 1
    assert taipei["sessions"][0]["local_date"] == "2026-07-05"
    assert taipei["sessions"][1]["local_date"] == "2026-07-06"


def test_missing_start_time_is_singleton_with_quality_note() -> None:
    """Missing start_time prevents forced grouping and is reported."""
    bundle = build_session_bundle(
        [_activity("known.tcx", START), _activity("missing.tcx", None)]
    )
    assert len(bundle["sessions"]) == 2
    missing = bundle["sessions"][1]
    assert missing["activity_count"] == 1
    assert missing["grouping_source"] == "missing_start_time_singleton"
    assert missing["data_quality"][
        "activities_missing_start_time_count"
    ] == 1
    assert bundle["data_quality"][
        "activities_missing_start_time_count"
    ] == 1


def test_activity_entries_never_infer_roles() -> None:
    """Each source TCX remains a distinct activity with a null role."""
    bundle = build_session_bundle(
        [
            _activity("one.tcx", START),
            _activity("two.tcx", START + timedelta(minutes=10)),
        ]
    )
    entries = bundle["sessions"][0]["activities"]
    assert len(entries) == 2
    assert all(item["role"] is None for item in entries)
    assert all(item["role_source"] == "not_inferred" for item in entries)
    assert all(
        lap["role"] is None
        for item in entries
        for lap in item["lap_summary"]
    )


def test_session_aggregates_use_fixed_formulas() -> None:
    """Session totals, weighted HR, and maximum HR are numeric formulas."""
    bundle = build_session_bundle(
        [
            _activity(
                "one.tcx",
                START,
                distance_meters=4000.0,
                duration_seconds=600.0,
                average_hr=150,
                maximum_hr=165,
            ),
            _activity(
                "two.tcx",
                START + timedelta(minutes=20),
                distance_meters=6000.0,
                duration_seconds=1200.0,
                average_hr=170,
                maximum_hr=180,
            ),
        ]
    )
    session = bundle["sessions"][0]
    assert session["total_distance_km"] == 10.0
    assert session["total_duration_minutes"] == 30.0
    assert session["weighted_average_heart_rate_bpm"] == 163.3
    assert session["maximum_heart_rate_bpm"] == 180


def test_session_manual_context_is_placeholder_only() -> None:
    """Manual context fields are null placeholders, never TCX guesses."""
    context = build_session_bundle(
        [_activity("one.tcx", START)]
    )["sessions"][0]["manual_context"]
    assert context == {
        "planned_workout_text": None,
        "planned_workout_source": "manual_only",
        "completion": None,
        "rpe_1_to_10": None,
        "pain_before": None,
        "pain_during": None,
        "pain_after": None,
        "next_day_status": None,
    }


def test_session_cadence_and_power_aggregate_trackpoints() -> None:
    """Session cadence/power metrics aggregate raw trackpoint samples."""
    session = build_session_bundle(
        [
            _activity("one.tcx", START, run_cadence=80, power=220),
            _activity(
                "two.tcx",
                START + timedelta(minutes=20),
                run_cadence=90,
                power=240,
            ),
        ]
    )["sessions"][0]
    cadence = session["cadence"]
    power = session["power"]
    assert cadence["avg_run_cadence_raw"] == 85.0
    assert cadence["max_run_cadence_raw"] == 90
    assert cadence["trackpoints_with_run_cadence_count"] == 2
    assert cadence["avg_cadence_spm"] is None
    assert cadence["conversion_rule"] is None
    assert power["avg_watts"] == 230.0
    assert power["max_watts"] == 240
    assert power["trackpoints_with_power_count"] == 2
    assert session["data_quality"]["trackpoints_with_power_count"] == 2
    assert (
        session["data_quality"]["trackpoints_with_run_cadence_count"] == 2
    )


def test_activity_entries_include_local_time_and_raw_metrics() -> None:
    """Each bundled activity carries coach-ready factual metric fields."""
    activity = build_session_bundle(
        [_activity("one.tcx", START, run_cadence=82, power=210)]
    )["sessions"][0]["activities"][0]
    assert activity["activity_summary"]["start_time_local"] == (
        "2026-07-05T14:00:00+08:00"
    )
    assert activity["activity_summary"]["timezone"] == "Asia/Taipei"
    assert activity["activity_summary"]["local_date"] == "2026-07-05"
    assert activity["key_metrics"]["cadence"]["avg_run_cadence_raw"] == 82.0
    assert activity["key_metrics"]["cadence"]["avg_cadence_spm"] is None
    assert activity["key_metrics"]["cadence"]["conversion_rule"] is None
    assert activity["key_metrics"]["power"]["avg_watts"] == 210.0
    assert activity["lap_summary"][0]["pace_reliability"] == "high"
    assert activity["lap_summary"][0]["reliability_reason"] == (
        "lap_distance_at_least_0.3km"
    )
    assert activity["computed_split_metrics"]["interpretation_level"] == (
        "limited_for_interval_or_mixed_lap_activity"
    )


def test_session_id_and_grouping_rule_are_stable() -> None:
    """Candidate identifiers and grouping rule are explicit."""
    session = build_session_bundle([_activity("one.tcx", START)])["sessions"][0]
    assert session["session_id"] == "2026-07-05_Running_001"
    assert session["grouping_rule"] == {
        "same_local_date": True,
        "timezone": "Asia/Taipei",
        "same_sport": True,
        "max_gap_minutes": 30,
    }
    assert session["start_time_local"] == "2026-07-05T14:00:00+08:00"
    assert session["end_time_local"] == "2026-07-05T14:10:00+08:00"
    assert session["timezone"] == "Asia/Taipei"
    assert session["local_date"] == "2026-07-05"


def test_bundle_privacy_excludes_coordinates_and_routes() -> None:
    """Bundle never serializes trackpoint GPS or route details."""
    bundle = build_session_bundle([_activity("one.tcx", START)])
    text = json.dumps(bundle).lower()
    assert bundle["privacy"]["gps_coordinates_included"] is False
    assert bundle["privacy"]["route_details_included"] is False
    for value in ("latitude", "longitude", "23.456789", "120.987654"):
        assert value not in text


def test_bundle_contains_no_role_or_advice_semantics() -> None:
    """Bundle output contains no inferred workout labels or active advice."""
    text = json.dumps(
        build_session_bundle([_activity("one.tcx", START)])
    ).lower()
    for role in PROHIBITED_ROLES:
        assert role not in text
    for phrase in ("you should", "we recommend", "suggested question"):
        assert phrase not in text


def test_markdown_has_fixed_sections_and_no_sensitive_content() -> None:
    """Session Markdown is factual, structured, and GPS-free."""
    markdown = render_session_bundle_markdown(
        build_session_bundle([_activity("one.tcx", START)])
    )
    lines = markdown.splitlines()
    assert lines[0] == "# TCX Multi-Activity Report"
    assert lines[1] == "# TCX 多活動報告"
    assert (
        "This report packages one or more TCX activities for AI-readable "
        "review. It does not merge them into one recorded workout."
        in markdown
    )
    assert (
        "這並不代表將它們合併為單次記錄的運動"
        in markdown
    )
    assert (
        "Session candidates are candidate activity groups for review; "
        "they do not merge activities into one recorded workout."
        in markdown
    )
    assert (
        "Session 候選分組為供審閱的候選活動分組"
        in markdown
    )
    assert (
        "Manual context fields are placeholders only and were not "
        "inferred from TCX."
        in markdown
    )
    assert (
        "Cadence values are raw Garmin RunCadence values; no "
        "cadence x2 conversion is applied."
        in markdown
    )
    for heading in (
        "## Data Policy",
        "## 資料政策",
        "## Export Scope",
        "## 輸出範圍",
        "## Session Candidates",
        "## Session 候選分組",
        "## Activities",
        "## 活動紀錄",
        "## Lap Summaries",
        "## Lap 摘要",
        "## Computed Split Metrics",
        "## 固定公式分段指標",
        "## Data Quality",
        "## 資料品質",
        "## Privacy",
        "## 隱私保護",
    ):
        assert heading in markdown
    
    # Verify new polished wording and absence of old wording
    assert "課表／活動角色推論已停用" in markdown
    assert "角色：未標記（未推論）" in markdown
    assert "Session 候選分組" in markdown
    assert "運動角色推論" not in markdown
    assert "角色：無資料（未推論）" not in markdown
    assert "Session Candidate 候選分組" not in markdown

    lowered = markdown.lower()
    assert "Suggested AI Analysis Questions" not in markdown
    assert "latitude" not in lowered
    assert "longitude" not in lowered
    for role in PROHIBITED_ROLES:
        assert role not in lowered
    for phrase in MISLEADING_REPORT_WORDING:
        assert phrase not in lowered


def test_negative_gap_is_rejected() -> None:
    """A negative grouping gap is not a meaningful rule."""
    with pytest.raises(ValueError, match="max_gap_minutes"):
        build_session_bundle([], max_gap_minutes=-1)


def test_invalid_timezone_name_is_rejected() -> None:
    """Invalid timezone names raise instead of falling back silently."""
    with pytest.raises(ValueError, match="timezone_name"):
        build_session_bundle(
            [_activity("one.tcx", START)],
            timezone_name="Invalid/Zone",
        )
