"""Tests for the JSON and CSV exporters."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from garmin_tcx_ai.exporters import (
    CSV_COLUMNS,
    safe_activity_id,
    write_activity_json,
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
