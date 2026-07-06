"""Multi-lap parser tests for Garmin TCX files.

These tests exercise the activity-level aggregation logic in
``parse_tcx``: when a Running activity has multiple laps and no
activity-level aggregate elements, totals must be derived from the laps
(sum for time/distance/calories, max for speed/HR, average for HR).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from garmin_tcx_ai.parser import parse_tcx

FIXTURES = Path(__file__).parent / "fixtures"
TWO_LAP_RUNNING = FIXTURES / "two_lap_running.tcx"


def test_two_lap_fixture_parses() -> None:
    """The two-lap Running fixture parses without raising."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert result is not None
    assert result.activity.sport == "Running"


def test_two_laps_parsed_in_order() -> None:
    """Both laps are parsed and lap indices preserve source order."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert len(result.laps) == 2
    assert [lap.lap_index for lap in result.laps] == [1, 2]


def test_all_trackpoints_across_laps() -> None:
    """Trackpoints from both laps are collected with global ordering."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert len(result.trackpoints) == 4
    indices = [tp.trackpoint_index for tp in result.trackpoints]
    assert indices == [1, 2, 3, 4]


def test_trackpoints_reference_their_lap() -> None:
    """Each trackpoint records the lap it belongs to."""
    result = parse_tcx(TWO_LAP_RUNNING)
    lap_indices = [tp.lap_index for tp in result.trackpoints]
    assert lap_indices == [1, 1, 2, 2]


def test_total_time_summed_from_laps() -> None:
    """Activity total_time_seconds is the sum of lap durations."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert result.activity.total_time_seconds == pytest.approx(660.0)


def test_distance_summed_from_laps() -> None:
    """Activity distance_meters is the sum of lap distances."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert result.activity.distance_meters == pytest.approx(2100.0)


def test_calories_summed_from_laps() -> None:
    """Activity calories is the sum of lap calories."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert result.activity.calories == 110


def test_max_speed_is_lap_maximum() -> None:
    """Activity maximum_speed_mps is the max across laps."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert result.activity.maximum_speed_mps == pytest.approx(4.0)


def test_max_hr_is_lap_maximum() -> None:
    """Activity maximum_heart_rate_bpm is the max across laps."""
    result = parse_tcx(TWO_LAP_RUNNING)
    assert result.activity.maximum_heart_rate_bpm == 165


def test_avg_hr_is_lap_average() -> None:
    """Activity average_heart_rate_bpm averages the lap averages."""
    result = parse_tcx(TWO_LAP_RUNNING)
    # (140 + 150) / 2 = 145
    assert result.activity.average_heart_rate_bpm == 145


def test_lap_level_fields_preserved() -> None:
    """Per-lap aggregates are read directly from each lap element."""
    result = parse_tcx(TWO_LAP_RUNNING)
    lap1, lap2 = result.laps
    assert lap1.distance_meters == pytest.approx(1000.0)
    assert lap2.distance_meters == pytest.approx(1100.0)
    assert lap1.maximum_heart_rate_bpm == 150
    assert lap2.maximum_heart_rate_bpm == 165


def test_parsing_does_not_modify_two_lap_fixture() -> None:
    """Parsing must not modify the raw two-lap fixture file."""
    mtime_before = TWO_LAP_RUNNING.stat().st_mtime
    parse_tcx(TWO_LAP_RUNNING)
    mtime_after = TWO_LAP_RUNNING.stat().st_mtime
    assert mtime_before == mtime_after
