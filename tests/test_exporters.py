"""Tests for the JSON and CSV exporters."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from garmin_tcx_ai.exporters import (
    CSV_COLUMNS,
    safe_activity_id,
    write_activity_json,
    write_ai_summary_json,
    write_ai_summary_markdown,
    write_session_bundle_json,
    write_session_bundle_markdown,
    write_trackpoints_csv,
)
from garmin_tcx_ai.models import (
    Activity,
    Lap,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
)
from garmin_tcx_ai.normalizer import normalize_activity

MISLEADING_REPORT_WORDING = (
    "merged workout",
    "merged session",
    "combined workout",
    "合併成一堂訓練",
    "合併成一堂課",
)


def _make_activity() -> ParsedActivity:
    """Build a normalized-looking ParsedActivity for exporter tests."""
    ts = datetime(2026, 5, 1, 6, 30, 0, tzinfo=timezone.utc)
    return ParsedActivity(
        source=SourceInfo(
            format="tcx",
            file_name="run.tcx",
            file_path="data/raw/run.tcx",
        ),
        privacy=PrivacyInfo(gps_policy="keep"),
        activity=Activity(
            sport="Running",
            activity_id="2026-05-01T06:30:00Z",
            start_time=ts,
            distance_meters=None,
        ),
        laps=[Lap(lap_index=1, start_time=ts)],
        trackpoints=[
            Trackpoint(
                trackpoint_index=1,
                lap_index=1,
                timestamp=ts,
                latitude=25.0,
                longitude=121.0,
                heart_rate_bpm=None,
                speed_mps=2.8,
            ),
        ],
    )


# --- safe_activity_id ------------------------------------------------------

def test_safe_activity_id_replaces_unsafe_chars() -> None:
    """Unsafe path characters are replaced with underscores."""
    result = safe_activity_id('2026-05-01T06:30:00Z')
    assert ":" not in result
    assert result == "2026-05-01T06_30_00Z"


def test_safe_activity_id_strips_trailing_dot_and_space() -> None:
    """Trailing dots and whitespace are stripped."""
    assert safe_activity_id("  name.  ") == "name"


def test_safe_activity_id_fallback_to_filename_stem() -> None:
    """Ids that sanitize to empty fall back to the source file stem."""
    # "..." strips to empty, triggering the filename fallback.
    assert safe_activity_id("...", "run.tcx") == "run"


def test_safe_activity_id_never_nested() -> None:
    """A safe id never contains a path separator."""
    result = safe_activity_id("a/b\\c")
    assert "/" not in result and "\\" not in result


# --- JSON exporter ---------------------------------------------------------

def test_write_activity_json_creates_file(tmp_path: Path) -> None:
    """activity.json is written under a safe activity folder."""
    path = write_activity_json(_make_activity(), tmp_path)
    assert path.exists()
    assert path.name == "activity.json"
    # Folder is the safe id, not the raw activity_id with colons.
    assert path.parent.name == "2026-05-01T06_30_00Z"


def test_activity_json_top_level_keys(tmp_path: Path) -> None:
    """activity.json contains all required top-level keys."""
    path = write_activity_json(_make_activity(), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("source", "privacy", "activity", "laps",
                "trackpoints", "warnings"):
        assert key in data


def test_activity_json_none_becomes_null(tmp_path: Path) -> None:
    """Python None is serialized as JSON null."""
    path = write_activity_json(_make_activity(), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["activity"]["distance_meters"] is None
    assert data["trackpoints"][0]["heart_rate_bpm"] is None


def test_activity_json_datetime_is_iso8601(tmp_path: Path) -> None:
    """datetime values are serialized as ISO 8601 strings."""
    path = write_activity_json(_make_activity(), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["activity"]["start_time"] == "2026-05-01T06:30:00Z"
    assert data["trackpoints"][0]["timestamp"] == "2026-05-01T06:30:00Z"


def test_activity_json_does_not_use_raw_id_folder(tmp_path: Path) -> None:
    """The raw activity_id (with colons) is not used as a folder name."""
    write_activity_json(_make_activity(), tmp_path)
    assert not (tmp_path / "2026-05-01T06:30:00Z").exists()


# --- CSV exporter ----------------------------------------------------------

def test_write_trackpoints_csv_creates_file(tmp_path: Path) -> None:
    """trackpoints.csv is written under a safe activity folder."""
    path = write_trackpoints_csv(_make_activity(), tmp_path)
    assert path.exists()
    assert path.name == "trackpoints.csv"


def test_csv_header_order_matches_contract(tmp_path: Path) -> None:
    """CSV header order matches the data contract exactly."""
    path = write_trackpoints_csv(_make_activity(), tmp_path)
    with path.open(encoding="utf-8", newline="") as fh:
        header = next(csv.reader(fh))
    assert header == CSV_COLUMNS


def test_csv_missing_values_are_blank(tmp_path: Path) -> None:
    """Missing values are written as empty cells."""
    path = write_trackpoints_csv(_make_activity(), tmp_path)
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["heart_rate_bpm"] == ""
    assert rows[0]["power_watts"] == ""


def test_csv_reflects_remove_gps_policy(tmp_path: Path) -> None:
    """GPS columns are blank when the remove policy is applied."""
    normalized = normalize_activity(_make_activity(), "remove")
    path = write_trackpoints_csv(normalized, tmp_path)
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["latitude"] == ""
    assert rows[0]["longitude"] == ""


def test_csv_keeps_gps_with_keep_policy(tmp_path: Path) -> None:
    """GPS columns are populated when the keep policy is applied."""
    path = write_trackpoints_csv(_make_activity(), tmp_path)
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["latitude"] == "25.0"
    assert rows[0]["longitude"] == "121.0"


def test_csv_is_utf8(tmp_path: Path) -> None:
    """The CSV file is readable as UTF-8."""
    path = write_trackpoints_csv(_make_activity(), tmp_path)
    # Should not raise.
    path.read_text(encoding="utf-8")


# --- AI summary JSON exporter ----------------------------------------------

def test_write_ai_summary_json_creates_file(tmp_path: Path) -> None:
    """ai_summary.json is written under a safe activity folder."""
    path = write_ai_summary_json(_make_activity(), tmp_path)
    assert path.exists()
    assert path.name == "ai_summary.json"
    assert path.parent.name == "2026-05-01T06_30_00Z"


def test_ai_summary_json_top_level_keys(tmp_path: Path) -> None:
    """ai_summary.json contains all required top-level keys."""
    path = write_ai_summary_json(_make_activity(), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("activity_summary", "key_metrics", "lap_summary",
                "computed_split_metrics", "privacy", "data_quality",
                "data_policy"):
        assert key in data


def test_ai_summary_json_none_becomes_null(tmp_path: Path) -> None:
    """Missing values are serialized as JSON null."""
    path = write_ai_summary_json(_make_activity(), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    # _make_activity has no distance, so pace cannot be computed.
    metrics = data["key_metrics"]
    assert metrics["average_pace_seconds_per_km"] is None
    assert metrics["average_pace_formatted"] is None


def test_ai_summary_json_datetime_is_iso8601(tmp_path: Path) -> None:
    """datetime values are serialized as ISO 8601 strings."""
    path = write_ai_summary_json(_make_activity(), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    start = data["activity_summary"]["start_time"]
    assert start == "2026-05-01T06:30:00Z"
    assert data["lap_summary"][0]["start_time"] == start


def test_ai_summary_json_uses_safe_folder(tmp_path: Path) -> None:
    """The raw activity_id (with colons) is not used as a folder."""
    write_ai_summary_json(_make_activity(), tmp_path)
    assert not (tmp_path / "2026-05-01T06:30:00Z").exists()


# --- AI summary Markdown exporter -------------------------------------------

def test_write_ai_summary_markdown_creates_file(
    tmp_path: Path,
) -> None:
    """ai_summary.md is written under a safe activity folder."""
    path = write_ai_summary_markdown(_make_activity(), tmp_path)
    assert path.exists()
    assert path.name == "ai_summary.md"
    assert path.parent.name == "2026-05-01T06_30_00Z"


def test_ai_summary_markdown_has_fixed_sections(
    tmp_path: Path,
) -> None:
    """ai_summary.md contains every fixed section heading."""
    path = write_ai_summary_markdown(_make_activity(), tmp_path)
    text = path.read_text(encoding="utf-8")
    for heading in (
        "# Running Activity Summary",
        "## Activity",
        "## Key Metrics",
        "## Lap Summary",
        "## Computed Split Metrics",
        "## Elevation",
        "## Data Quality Notes",
        "## Privacy Notes",
        "## Data Policy",
    ):
        assert heading in text


def test_ai_summary_markdown_has_no_gps(tmp_path: Path) -> None:
    """ai_summary.md never contains coordinates, even with keep."""
    activity = _make_activity()  # keeps latitude=25.0/longitude=121.0
    path = write_ai_summary_markdown(activity, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "latitude" not in text.lower()
    assert "longitude" not in text.lower()
    assert "25.0" not in text
    assert "121.0" not in text


def test_ai_summary_markdown_no_coaching_or_medical(
    tmp_path: Path,
) -> None:
    """ai_summary.md contains no coaching or medical advice."""
    path = write_ai_summary_markdown(_make_activity(), tmp_path)
    text = path.read_text(encoding="utf-8").lower()
    for phrase in (
        "you should",
        "we recommend",
        "training plan",
        "medical advice",
        "diagnosis",
        "as your coach",
    ):
        assert phrase not in text


# --- Session bundle exporters ---------------------------------------------


def _make_session_activities() -> list[ParsedActivity]:
    """Build two activities for session exporter tests."""
    first = _make_activity()
    second = _make_activity()
    second.source.file_name = "run-2.tcx"
    second.activity.activity_id = "2026-05-01T06:50:00Z"
    second.activity.start_time = (
        first.activity.start_time + timedelta(minutes=20)
    )
    second.laps[0].start_time = second.activity.start_time
    second.trackpoints[0].timestamp = second.activity.start_time
    return [second, first]


def test_write_session_bundle_json_creates_fixed_path(
    tmp_path: Path,
) -> None:
    """JSON exporter returns the fixed session bundle path."""
    path = write_session_bundle_json(_make_session_activities(), tmp_path)
    assert isinstance(path, Path)
    assert path == tmp_path / "session_bundle" / "session_bundle.json"
    assert path.exists()


def test_session_bundle_json_has_complete_top_level_keys(
    tmp_path: Path,
) -> None:
    """Written session JSON contains every contract section."""
    path = write_session_bundle_json(_make_session_activities(), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {
        "schema_version",
        "export_scope",
        "data_policy",
        "sessions",
        "data_quality",
        "privacy",
    }
    assert data["export_scope"]["activity_count"] == 2
    assert data["export_scope"]["contains_multiple_activities"] is True
    assert "schema_version" in data
    assert "export_scope" in data
    assert "data_policy" in data
    assert "sessions" in data
    assert "session_candidate_count" in data["export_scope"]


def test_single_activity_session_bundle_json_is_standard_output(
    tmp_path: Path,
) -> None:
    """A single TCX still writes the coach-facing session bundle."""
    activity = _make_activity()
    activity.trackpoints[0].run_cadence_spm = 82
    activity.trackpoints[0].power_watts = 210
    path = write_session_bundle_json([activity], tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert path == tmp_path / "session_bundle" / "session_bundle.json"
    assert data["export_scope"]["activity_count"] == 1
    assert data["export_scope"]["session_candidate_count"] == 1
    assert data["export_scope"]["contains_multiple_activities"] is False
    assert data["sessions"][0]["manual_context"]["completion"] is None
    assert data["sessions"][0]["timezone"] == "Asia/Taipei"
    assert data["sessions"][0]["local_date"] == "2026-05-01"
    activity = data["sessions"][0]["activities"][0]
    assert activity["activity_summary"]["start_time_local"] == (
        "2026-05-01T14:30:00+08:00"
    )
    assert activity["key_metrics"]["cadence"]["avg_run_cadence_raw"] == 82.0
    assert activity["key_metrics"]["cadence"]["avg_cadence_spm"] is None
    assert activity["key_metrics"]["cadence"]["conversion_rule"] is None
    assert activity["key_metrics"]["power"]["avg_watts"] == 210.0


def test_write_session_bundle_markdown_creates_fixed_path(
    tmp_path: Path,
) -> None:
    """Markdown exporter returns the fixed session bundle path."""
    path = write_session_bundle_markdown(
        _make_session_activities(), tmp_path
    )
    assert isinstance(path, Path)
    assert path == tmp_path / "session_bundle" / "session_bundle.md"
    assert path.exists()


def test_single_activity_session_bundle_markdown_is_standard_output(
    tmp_path: Path,
) -> None:
    """A single TCX writes session_bundle.md with coach-facing sections."""
    activity = _make_activity()
    activity.trackpoints[0].run_cadence_spm = 82
    activity.trackpoints[0].power_watts = 210
    path = write_session_bundle_markdown([activity], tmp_path)
    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# TCX Multi-Activity Report"
    assert (
        "does not merge them into one recorded workout"
        in text
    )
    assert path == tmp_path / "session_bundle" / "session_bundle.md"
    assert "- Activities: 1" in text
    assert "- Session candidates: 1" in text
    assert "- Local date: 2026-05-01" in text
    assert "- Timezone: Asia/Taipei" in text
    assert "- Average run cadence raw: 82.0" in text
    assert "- Average watts: 210.0" in text
    assert "Pace reliability" in text
    assert "Reliability reason" in text
    assert "Avg cadence raw" in text
    assert "Avg watts" in text
    assert "Interpretation level:" in text


def test_session_bundle_markdown_is_factual_and_private(
    tmp_path: Path,
) -> None:
    """Written Markdown has fixed sections and no forbidden output."""
    path = write_session_bundle_markdown(
        _make_session_activities(), tmp_path
    )
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    for heading in (
        "# TCX Multi-Activity Report",
        "## Data Policy",
        "## Export Scope",
        "## Session Candidates",
        "## Activities",
        "## Lap Summaries",
        "## Computed Split Metrics",
        "## Data Quality",
        "## Privacy",
    ):
        assert heading in text
    assert "Suggested AI Analysis Questions" not in text
    assert (
        "Session candidates are candidate activity groups for review"
        in text
    )
    assert (
        "does not merge them into one recorded workout"
        in text
    )
    for phrase in (
        "latitude",
        "longitude",
        "warmup",
        "cooldown",
        "you should",
        "we recommend",
    ):
        assert phrase not in lowered
    for phrase in MISLEADING_REPORT_WORDING:
        assert phrase not in lowered
