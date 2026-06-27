"""Parser tests for Garmin TCX files."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from garmin_tcx_ai.parser import (
    TCXParseError,
    UnsupportedActivityError,
    parse_tcx,
)

FIXTURES = Path(__file__).parent / "fixtures"
MINIMAL_RUNNING = FIXTURES / "minimal_running.tcx"
INVALID_TCX = FIXTURES / "invalid.tcx"
CYCLING_TCX = FIXTURES / "cycling_activity.tcx"


# ---------------------------------------------------------------------------
# 1. Happy-path: minimal Running fixture parses successfully
# ---------------------------------------------------------------------------

def test_parse_minimal_running_succeeds() -> None:
    """The minimal Running fixture parses without raising."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert result is not None


# ---------------------------------------------------------------------------
# 2. ParsedActivity top-level structure
# ---------------------------------------------------------------------------

def test_parsed_activity_has_required_sections() -> None:
    """ParsedActivity exposes source, privacy, activity, laps, trackpoints,
    and warnings."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert result.source is not None
    assert result.privacy is not None
    assert result.activity is not None
    assert isinstance(result.laps, list)
    assert isinstance(result.trackpoints, list)
    assert isinstance(result.warnings, list)


# ---------------------------------------------------------------------------
# 3. Activity-level fields
# ---------------------------------------------------------------------------

def test_activity_sport_and_id() -> None:
    """Running sport and activity_id are parsed correctly."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert result.activity.sport == "Running"
    assert result.activity.activity_id == "2000-01-01T00:00:00Z"


def test_activity_start_time_is_datetime() -> None:
    """start_time is a datetime object derived from activity_id."""
    from datetime import timezone

    result = parse_tcx(MINIMAL_RUNNING)
    st = result.activity.start_time
    assert st is not None
    assert st.tzinfo == timezone.utc
    assert st.year == 2000


# ---------------------------------------------------------------------------
# 4. Lap count and trackpoint count
# ---------------------------------------------------------------------------

def test_lap_count_matches_fixture() -> None:
    """Exactly one lap is parsed from the fixture."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert len(result.laps) == 1


def test_trackpoint_count_matches_fixture() -> None:
    """Exactly two trackpoints are parsed from the fixture."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert len(result.trackpoints) == 2


# ---------------------------------------------------------------------------
# 5. Order preservation
# ---------------------------------------------------------------------------

def test_lap_order_preserved() -> None:
    """Lap indices are assigned in source order, starting at 1."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert result.laps[0].lap_index == 1


def test_trackpoint_order_preserved() -> None:
    """Trackpoint indices increase monotonically from 1."""
    result = parse_tcx(MINIMAL_RUNNING)
    indices = [tp.trackpoint_index for tp in result.trackpoints]
    assert indices == list(range(1, len(indices) + 1))


def test_trackpoints_reference_correct_lap() -> None:
    """All trackpoints in a single-lap fixture have lap_index == 1."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert all(tp.lap_index == 1 for tp in result.trackpoints)


# ---------------------------------------------------------------------------
# 6. Garmin extension fields
# ---------------------------------------------------------------------------

def test_extension_speed_parsed() -> None:
    """speed_mps is populated from ns3:Speed extension."""
    result = parse_tcx(MINIMAL_RUNNING)
    speeds = [tp.speed_mps for tp in result.trackpoints]
    assert all(s is not None for s in speeds)
    assert speeds[0] == pytest.approx(3.0)
    assert speeds[1] == pytest.approx(3.2)


def test_extension_run_cadence_parsed() -> None:
    """run_cadence_spm is populated from ns3:RunCadence extension."""
    result = parse_tcx(MINIMAL_RUNNING)
    cadences = [tp.run_cadence_spm for tp in result.trackpoints]
    assert cadences == [80, 82]


def test_extension_watts_parsed() -> None:
    """power_watts is populated from ns3:Watts extension."""
    result = parse_tcx(MINIMAL_RUNNING)
    watts = [tp.power_watts for tp in result.trackpoints]
    assert watts == [180, 185]


def test_pace_derived_from_speed() -> None:
    """pace_seconds_per_km is derived as 1000 / speed_mps."""
    result = parse_tcx(MINIMAL_RUNNING)
    tp = result.trackpoints[0]
    assert tp.speed_mps is not None and tp.speed_mps > 0
    expected_pace = round(1000.0 / tp.speed_mps, 2)
    assert tp.pace_seconds_per_km == pytest.approx(expected_pace)


# ---------------------------------------------------------------------------
# 7. Missing optional fields become None (not a crash)
# ---------------------------------------------------------------------------

def test_missing_activity_level_hr_is_none() -> None:
    """average/maximum_heart_rate_bpm at activity level are None when
    not in the fixture."""
    result = parse_tcx(MINIMAL_RUNNING)
    # The minimal fixture has no activity-level HR aggregate elements
    assert result.activity.average_heart_rate_bpm is None
    assert result.activity.maximum_heart_rate_bpm is None


def test_missing_lap_level_hr_is_none() -> None:
    """Lap-level average/maximum HR are None when absent from the fixture."""
    result = parse_tcx(MINIMAL_RUNNING)
    lap = result.laps[0]
    assert lap.average_heart_rate_bpm is None
    assert lap.maximum_heart_rate_bpm is None


# ---------------------------------------------------------------------------
# 8. Warning record schema
# ---------------------------------------------------------------------------

def test_warning_records_have_required_fields() -> None:
    """Any warning emitted by the parser has code, severity, field, message,
    and source_file."""
    result = parse_tcx(MINIMAL_RUNNING)
    for w in result.warnings:
        assert hasattr(w, "code") and w.code
        assert w.severity in ("info", "warning", "error")
        assert hasattr(w, "field")
        assert hasattr(w, "message") and w.message
        assert hasattr(w, "source_file") and w.source_file


# ---------------------------------------------------------------------------
# 9. Invalid XML produces a readable parser error
# ---------------------------------------------------------------------------

def test_invalid_xml_raises_tcx_parse_error() -> None:
    """Malformed XML raises TCXParseError with a readable message."""
    with pytest.raises(TCXParseError) as exc_info:
        parse_tcx(INVALID_TCX)
    assert "invalid.tcx" in str(exc_info.value).lower() or \
        "invalid" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 10. Unsupported activity type is not silently parsed as Running
# ---------------------------------------------------------------------------

def test_unsupported_sport_raises_error() -> None:
    """A Biking TCX raises UnsupportedActivityError and is not parsed as
    Running."""
    with pytest.raises(UnsupportedActivityError) as exc_info:
        parse_tcx(CYCLING_TCX)
    msg = str(exc_info.value)
    assert "Biking" in msg or "supported" in msg.lower()


# ---------------------------------------------------------------------------
# 11. source_file in warnings does not expose full local path
# ---------------------------------------------------------------------------

def test_source_file_in_warnings_is_filename_only() -> None:
    """source_file in any warning must be just the filename, not an abs path.

    We force a warning by using the minimal fixture and checking any
    produced warning. We also verify the source metadata itself.
    """
    result = parse_tcx(MINIMAL_RUNNING)
    for w in result.warnings:
        assert os.sep not in w.source_file, (
            f"source_file '{w.source_file}' must not contain path separators"
        )
        assert not Path(w.source_file).is_absolute(), (
            f"source_file '{w.source_file}' must not be an absolute path"
        )
    # source.file_name should also be filename-only
    assert result.source.file_name == "minimal_running.tcx"


# ---------------------------------------------------------------------------
# 12. Parsing does not modify the fixture file
# ---------------------------------------------------------------------------

def test_parsing_does_not_modify_fixture() -> None:
    """The raw TCX fixture is not modified during parsing."""
    mtime_before = MINIMAL_RUNNING.stat().st_mtime
    parse_tcx(MINIMAL_RUNNING)
    mtime_after = MINIMAL_RUNNING.stat().st_mtime
    assert mtime_before == mtime_after, (
        "Parsing must not modify the source TCX file"
    )


# ---------------------------------------------------------------------------
# 13. Missing file produces a clear error
# ---------------------------------------------------------------------------

def test_missing_file_raises_file_not_found() -> None:
    """Passing a non-existent path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_tcx(FIXTURES / "does_not_exist.tcx")


# ---------------------------------------------------------------------------
# 14. Lap fields parsed correctly
# ---------------------------------------------------------------------------

def test_lap_fields_from_fixture() -> None:
    """Lap-level fields match the fixture values."""
    result = parse_tcx(MINIMAL_RUNNING)
    lap = result.laps[0]
    assert lap.total_time_seconds == pytest.approx(60.0)
    assert lap.distance_meters == pytest.approx(200.0)
    assert lap.calories == 10
    assert lap.intensity == "Active"
    assert lap.trigger_method == "Manual"


# ---------------------------------------------------------------------------
# 15. Activity aggregates derived from laps when absent at activity level
# ---------------------------------------------------------------------------

def test_activity_totals_derived_from_laps() -> None:
    """total_time_seconds, distance_meters, and calories are summed from
    laps when no activity-level aggregate element exists."""
    result = parse_tcx(MINIMAL_RUNNING)
    assert result.activity.total_time_seconds == pytest.approx(60.0)
    assert result.activity.distance_meters == pytest.approx(200.0)
    assert result.activity.calories == 10
