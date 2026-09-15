"""Unit tests for the plain-text AI export module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from garmin_tcx_ai import ai_text
from garmin_tcx_ai.models import (
    Activity,
    Lap,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
)
from garmin_tcx_ai.normalizer import normalize_activity
from garmin_tcx_ai.parser import parse_tcx

FIXTURES = Path(__file__).parent / "fixtures"
TAIPEI = timezone(timedelta(hours=8))


def _fixture(name: str) -> ParsedActivity:
    return normalize_activity(parse_tcx(FIXTURES / name), gps_policy="keep")


def _synthetic(
    start: datetime,
    lap_specs: list[tuple[int, float]],
    file_name: str = "synthetic.tcx",
) -> ParsedActivity:
    """Build an activity with one-second trackpoints per lap.

    ``lap_specs`` is a list of ``(seconds, metres)`` tuples.
    """
    laps: list[Lap] = []
    points: list[Trackpoint] = []
    clock = start
    cumulative = 0.0
    index = 0
    for lap_index, (seconds, metres) in enumerate(lap_specs, start=1):
        laps.append(
            Lap(
                lap_index=lap_index,
                start_time=clock,
                total_time_seconds=float(seconds),
                distance_meters=metres,
                average_heart_rate_bpm=140 + lap_index,
                maximum_heart_rate_bpm=160 + lap_index,
                trigger_method="Manual",
            )
        )
        for second in range(seconds + 1):
            points.append(
                Trackpoint(
                    trackpoint_index=index,
                    lap_index=lap_index,
                    timestamp=clock + timedelta(seconds=second),
                    latitude=25.0,
                    longitude=121.5,
                    altitude_meters=10.0 + second * 0.01,
                    distance_meters=cumulative + metres * second / seconds,
                    heart_rate_bpm=130 + lap_index,
                    run_cadence_spm=85,
                    power_watts=200,
                )
            )
            index += 1
        clock += timedelta(seconds=seconds)
        cumulative += metres
    total_seconds = sum(s for s, _ in lap_specs)
    total_metres = sum(m for _, m in lap_specs)
    return ParsedActivity(
        source=SourceInfo(format="tcx", file_name=file_name, file_path=""),
        privacy=PrivacyInfo(gps_policy="keep"),
        activity=Activity(
            sport="Running",
            activity_id="synthetic",
            start_time=start,
            total_time_seconds=float(total_seconds),
            distance_meters=total_metres,
            average_heart_rate_bpm=145,
            maximum_heart_rate_bpm=170,
        ),
        laps=laps,
        trackpoints=points,
    )


def test_write_ai_text_outputs_creates_expected_files(
    tmp_path: Path,
) -> None:
    """summary.txt, all_in_one.txt and one runs/*.txt per activity."""
    activities = [
        _fixture("minimal_running.tcx"),
        _fixture("two_lap_running.tcx"),
    ]
    paths = ai_text.write_ai_text_outputs(activities, tmp_path)

    assert paths.summary_path == tmp_path / "summary.txt"
    assert paths.all_in_one_path == tmp_path / "all_in_one.txt"
    assert len(paths.run_paths) == 2
    for path in [paths.summary_path, paths.all_in_one_path, *paths.run_paths]:
        assert path.is_file()
        assert path.suffix == ".txt"
    assert all(p.parent == tmp_path / "runs" for p in paths.run_paths)


def test_activity_text_never_contains_gps(tmp_path: Path) -> None:
    """Latitude/longitude values from the fixture are never written."""
    activity = _fixture("minimal_running.tcx")
    assert activity.trackpoints[0].latitude is not None
    text = ai_text.render_activity_text(activity, TAIPEI, "Asia/Taipei")
    assert "0.0105" not in text
    assert "latitude" not in text.lower()
    assert "GPS" in text


def test_activity_text_contains_overview_and_lap_rows() -> None:
    """The overview lines and a lap table row are rendered."""
    activity = _fixture("two_lap_running.tcx")
    text = ai_text.render_activity_text(activity, TAIPEI, "Asia/Taipei")
    assert "跑步記錄:" in text
    assert "--- 每圈 (Lap) ---" in text
    assert "--- 軌跡取樣 ---" in text
    lap_rows = [
        line for line in text.splitlines()
        if line.startswith(("1 | ", "2 | "))
    ]
    assert len(lap_rows) == 2


def test_sampling_keeps_short_laps_dense_and_long_laps_sparse() -> None:
    """A 60 s interval lap keeps ~5 s spacing; a 20 min lap uses 30 s."""
    start = datetime(2026, 7, 6, 10, 0, tzinfo=UTC)
    activity = _synthetic(start, [(60, 250.0), (1200, 3000.0)])
    text = ai_text.render_activity_text(activity, TAIPEI, "Asia/Taipei")
    rows = [
        line.split(" | ")
        for line in text.splitlines()
        if line[:1].isdigit() and line.count(" | ") == 7
    ]
    short_rows = [r for r in rows if r[1] == "1"]
    long_rows = [r for r in rows if r[1] == "2"]
    # 60 s / 5 s = 12 intervals -> 13 samples (first + every 5 s + last).
    assert len(short_rows) == 13
    # 1200 s / 30 s = 40 intervals -> 41 samples.
    assert len(long_rows) == 41


def test_sampling_density_changes_row_count() -> None:
    """compact produces fewer rows than detailed for the same lap."""
    start = datetime(2026, 7, 6, 10, 0, tzinfo=UTC)
    activity = _synthetic(start, [(600, 1500.0)])
    counts = {}
    for density in ai_text.DENSITY_CHOICES:
        text = ai_text.render_activity_text(
            activity, TAIPEI, "Asia/Taipei", density
        )
        counts[density] = sum(
            1 for line in text.splitlines()
            if line[:1].isdigit() and line.count(" | ") == 7
        )
    assert counts["compact"] < counts["standard"] < counts["detailed"]


def test_write_rejects_unknown_density(tmp_path: Path) -> None:
    """An unknown density name raises ValueError."""
    with pytest.raises(ValueError):
        ai_text.write_ai_text_outputs(
            [_fixture("minimal_running.tcx")], tmp_path, density="nope"
        )


def test_summary_weekly_totals_monday_to_sunday() -> None:
    """Runs on a Sunday and the next Monday land in different weeks."""
    sunday = datetime(2026, 7, 5, 2, 0, tzinfo=UTC)  # 10:00 local
    monday = datetime(2026, 7, 6, 2, 0, tzinfo=UTC)
    activities = [
        _synthetic(sunday, [(600, 2000.0)], "sun.tcx"),
        _synthetic(monday, [(600, 3000.0)], "mon.tcx"),
    ]
    text = ai_text.render_summary_text(activities, TAIPEI, "Asia/Taipei")
    assert "跑步次數: 2 | 總距離: 5.00 km" in text
    week_rows = [
        line for line in text.splitlines() if line.startswith("2026-W")
    ]
    assert len(week_rows) == 2
    assert week_rows[0].startswith("2026-W27 | 06/29~07/05 | 1 | 2.00")
    assert week_rows[1].startswith("2026-W28 | 07/06~07/12 | 1 | 3.00")


def test_summary_fills_empty_weeks_between_runs() -> None:
    """A week with no runs is still listed with zero counts."""
    first = datetime(2026, 6, 22, 2, 0, tzinfo=UTC)
    later = datetime(2026, 7, 6, 2, 0, tzinfo=UTC)
    activities = [
        _synthetic(first, [(600, 2000.0)], "a.tcx"),
        _synthetic(later, [(600, 2000.0)], "b.tcx"),
    ]
    text = ai_text.render_summary_text(activities, TAIPEI, "Asia/Taipei")
    week_rows = [
        line for line in text.splitlines() if line.startswith("2026-W")
    ]
    assert len(week_rows) == 3
    assert week_rows[1].startswith("2026-W27 | 06/29~07/05 | 0 | 0 | 0:00")


def test_summary_handles_missing_start_time() -> None:
    """Activities without start_time are counted but not dated."""
    activity = _fixture("minimal_running.tcx")
    activity.activity.start_time = None
    text = ai_text.render_summary_text([activity], TAIPEI, "Asia/Taipei")
    assert "缺少開始時間的活動: 1" in text
    assert "無可用日期" in text


def test_run_file_names_use_local_date_and_distance(
    tmp_path: Path,
) -> None:
    """File stems look like YYYY-MM-DD_HHMM_<km>km and never collide."""
    start = datetime(2026, 7, 6, 2, 30, tzinfo=UTC)
    activities = [
        _synthetic(start, [(600, 2000.0)], "a.tcx"),
        _synthetic(start, [(600, 2000.0)], "b.tcx"),
    ]
    paths = ai_text.write_ai_text_outputs(activities, tmp_path)
    names = sorted(p.name for p in paths.run_paths)
    assert names == [
        "2026-07-06_1030_2.00km.txt",
        "2026-07-06_1030_2.00km_2.txt",
    ]


def test_all_in_one_contains_summary_and_every_run(tmp_path: Path) -> None:
    """all_in_one.txt embeds the summary and each run text."""
    activities = [
        _fixture("minimal_running.tcx"),
        _fixture("two_lap_running.tcx"),
    ]
    paths = ai_text.write_ai_text_outputs(activities, tmp_path)
    all_text = paths.all_in_one_path.read_text(encoding="utf-8")
    assert paths.summary_path.read_text(encoding="utf-8") in all_text
    for run_path in paths.run_paths:
        assert run_path.read_text(encoding="utf-8") in all_text
    assert "每次跑步記錄 (共 2 次)" in all_text


def test_segment_pace_reports_pause_when_not_moving() -> None:
    """Almost no distance over a long gap is labelled as a pause."""
    start = datetime(2026, 7, 6, 2, 0, tzinfo=UTC)
    first = Trackpoint(timestamp=start, distance_meters=100.0)
    later = Trackpoint(
        timestamp=start + timedelta(seconds=90), distance_meters=101.0
    )
    assert ai_text._segment_pace(first, later) == "暫停"
    moving = Trackpoint(
        timestamp=start + timedelta(seconds=30), distance_meters=200.0
    )
    assert ai_text._segment_pace(first, moving) == "5:00"
