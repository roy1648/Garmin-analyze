"""Plain-text, AI-readable exports for Running activities.

This module turns normalized activities into UTF-8 ``.txt`` files that
can be handed to a chat AI directly:

* ``runs/<date>_<time>_<km>km.txt`` -- one file per activity with the
  activity overview, a per-lap table and an adaptively sampled
  trackpoint table. GPS coordinates are never written.
* ``summary.txt`` -- period totals, Monday-to-Sunday weekly totals,
  daily totals and one line per run.
* ``all_in_one.txt`` -- the summary followed by every run file, so the
  whole period can be pasted or uploaded in one go.

The text is factual only: no coaching, no zone inference, no cadence
conversion. Sampling keeps short laps (intervals) dense and long laps
sparse so the size stays small while interval structure survives.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from garmin_tcx_ai.models import ParsedActivity, Trackpoint

RUNS_DIR_NAME = "runs"
SUMMARY_FILE_NAME = "summary.txt"
ALL_IN_ONE_FILE_NAME = "all_in_one.txt"

#: Sampling interval in seconds for (short, medium, long) laps.
DENSITY_INTERVALS: dict[str, tuple[int, int, int]] = {
    "compact": (10, 30, 60),
    "standard": (5, 15, 30),
    "detailed": (1, 5, 10),
}
DENSITY_CHOICES = tuple(DENSITY_INTERVALS)
SHORT_LAP_SECONDS = 180
MEDIUM_LAP_SECONDS = 600
#: Slower than this between two samples is reported as a pause.
PAUSE_PACE_SECONDS_PER_KM = 1500.0

_WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
_RULE = "=" * 60


@dataclass(frozen=True)
class AiTextPaths:
    """Paths written by :func:`write_ai_text_outputs`."""

    summary_path: Path
    all_in_one_path: Path
    run_paths: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_ai_text_outputs(
    activities: list[ParsedActivity],
    output_dir: Path,
    timezone_name: str = "Asia/Taipei",
    density: str = "standard",
) -> AiTextPaths:
    """Write summary, per-run and all-in-one text files.

    Args:
        activities: Normalized activities (any order).
        output_dir: Folder that receives ``summary.txt``,
            ``all_in_one.txt`` and the ``runs/`` sub-folder.
        timezone_name: IANA zone used for local dates and times.
        density: One of :data:`DENSITY_CHOICES`.

    Returns:
        The written paths.
    """
    if density not in DENSITY_INTERVALS:
        raise ValueError(f"Unknown trackpoint density: {density!r}")
    zone = _zone(timezone_name)
    ordered = sorted(activities, key=_sort_key)

    runs_dir = Path(output_dir) / RUNS_DIR_NAME
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_paths: list[Path] = []
    run_texts: list[str] = []
    used_names: set[str] = set()
    for index, activity in enumerate(ordered, start=1):
        text = render_activity_text(
            activity, zone, timezone_name, density
        )
        stem = _run_file_stem(activity, zone, index)
        name = _unique_name(stem, used_names)
        target = runs_dir / f"{name}.txt"
        target.write_text(text, encoding="utf-8", newline="\n")
        run_paths.append(target)
        run_texts.append(text)

    summary_text = render_summary_text(ordered, zone, timezone_name)
    summary_path = Path(output_dir) / SUMMARY_FILE_NAME
    summary_path.write_text(summary_text, encoding="utf-8", newline="\n")

    all_text = render_all_in_one_text(summary_text, run_texts)
    all_path = Path(output_dir) / ALL_IN_ONE_FILE_NAME
    all_path.write_text(all_text, encoding="utf-8", newline="\n")

    return AiTextPaths(
        summary_path=summary_path,
        all_in_one_path=all_path,
        run_paths=run_paths,
    )


def render_activity_text(
    activity: ParsedActivity,
    zone: tzinfo,
    timezone_name: str,
    density: str = "standard",
) -> str:
    """Render one activity as plain text without GPS coordinates."""
    act = activity.activity
    local_start = _local(act.start_time, zone)
    title_date = _date_with_weekday(local_start)
    title_time = local_start.strftime("%H:%M") if local_start else "--:--"
    hr_values = _values(activity.trackpoints, "heart_rate_bpm")
    cad_values = _values(activity.trackpoints, "run_cadence_spm")
    pow_values = _values(activity.trackpoints, "power_watts")
    alt_values = _values(activity.trackpoints, "altitude_meters")
    avg_hr = act.average_heart_rate_bpm
    if avg_hr is None and hr_values:
        avg_hr = _avg(hr_values)
    max_hr = act.maximum_heart_rate_bpm
    if max_hr is None and hr_values:
        max_hr = max(hr_values)
    local_date = local_start.date().isoformat() if local_start else "未知"
    local_time = local_start.strftime("%H:%M:%S") if local_start else "未知"

    lines = [
        _RULE,
        f"跑步記錄: {title_date} {title_time} 開始",
        _RULE,
        f"來源檔案: {Path(activity.source.file_name).name}",
        f"運動類型: {act.sport or '未知'}",
        f"本地日期: {local_date} | 開始時間: {local_time} ({timezone_name})",
        f"總時間: {_fmt_duration(act.total_time_seconds)}",
        f"距離: {_fmt_km(act.distance_meters)}",
        (
            "平均配速: "
            f"{_fmt_pace(_pace(act.total_time_seconds, act.distance_meters))}"
            " /km"
        ),
        (
            f"平均心率: {_fmt_int(avg_hr, 'bpm')}"
            f" | 最高心率: {_fmt_int(max_hr, 'bpm')}"
        ),
        (
            "平均步頻 (Garmin RunCadence 原始值): "
            f"{_fmt_avg(cad_values)} | 最高: {_fmt_max(cad_values)}"
        ),
        (
            f"平均功率: {_fmt_avg(pow_values, 'W')}"
            f" | 最高: {_fmt_max(pow_values, 'W')}"
        ),
        f"高度: {_altitude_line(alt_values)}",
        f"卡路里: {_fmt_int(act.calories, 'kcal')}",
        (
            f"圈數: {len(activity.laps)}"
            f" | 軌跡點數: {len(activity.trackpoints)}"
        ),
        "",
        "--- 每圈 (Lap) ---",
    ]
    lines.extend(_lap_table(activity, zone))
    lines.append("")
    lines.append("--- 軌跡取樣 ---")
    lines.extend(_trackpoint_table(activity, density))
    lines.extend(
        [
            "",
            (
                "備註: 不含 GPS 座標。步頻為 Garmin RunCadence 原始值，"
                "未做 x2 換算。配速 = 時間 / 距離，未做任何訓練解讀。"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_summary_text(
    activities: list[ParsedActivity],
    zone: tzinfo,
    timezone_name: str,
) -> str:
    """Render period, weekly, daily and per-run totals as plain text."""
    ordered = sorted(activities, key=_sort_key)
    dated = [
        (_local(item.activity.start_time, zone), item) for item in ordered
    ]
    known = [(dt, item) for dt, item in dated if dt is not None]
    unknown = [item for dt, item in dated if dt is None]

    lines = [_RULE, "跑步訓練摘要", _RULE]
    if known:
        first_day = known[0][0].date().isoformat()
        last_day = known[-1][0].date().isoformat()
        lines.append(
            f"資料範圍: {first_day} ~ {last_day} (本地日期, {timezone_name})"
        )
    else:
        lines.append(f"資料範圍: 無可用日期 ({timezone_name})")
    lines.extend(_totals_lines(ordered))
    if unknown:
        lines.append(
            f"缺少開始時間的活動: {len(unknown)} (未列入週/日統計)"
        )

    lines.extend(["", "--- 週跑量 (週一至週日) ---"])
    lines.extend(_weekly_table(known))
    lines.extend(["", "--- 每日 ---"])
    lines.extend(_daily_table(known))
    lines.extend(["", "--- 每次跑步 ---"])
    lines.extend(_run_table(dated))
    lines.extend(
        [
            "",
            (
                "說明: 平均配速 = 總時間 / 總距離。平均心率為各次跑步"
                "平均心率的時間加權值。步頻為 Garmin RunCadence 原始值，"
                "未做 x2 換算。不含 GPS 座標，未做任何訓練解讀。"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_all_in_one_text(
    summary_text: str,
    run_texts: list[str],
) -> str:
    """Concatenate the summary and every run text into one document."""
    parts = [
        (
            "本檔案包含整段期間的跑步摘要與每一次跑步的記錄，"
            "可整份提供給 AI 進行課表規劃。"
        ),
        "",
        summary_text,
    ]
    if run_texts:
        parts.extend(
            ["", _RULE, f"每次跑步記錄 (共 {len(run_texts)} 次)", ""]
        )
        parts.extend(run_texts)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Activity sections
# ---------------------------------------------------------------------------


def _lap_table(activity: ParsedActivity, zone: tzinfo) -> list[str]:
    """Render the per-lap table."""
    if not activity.laps:
        return ["無 Lap 資料。"]
    lines = [
        (
            "圈 | 開始(本地) | 時間 | 距離(km) | 配速(/km) | 平均心率"
            " | 最高心率 | 平均步頻 | 平均功率 | 觸發"
        )
    ]
    for lap in activity.laps:
        points = [
            tp
            for tp in activity.trackpoints
            if tp.lap_index == lap.lap_index
        ]
        cad = _values(points, "run_cadence_spm")
        pwr = _values(points, "power_watts")
        lap_hr = _values(points, "heart_rate_bpm")
        hr_avg = lap.average_heart_rate_bpm
        hr_max = lap.maximum_heart_rate_bpm
        if hr_avg is None and lap_hr:
            hr_avg = _avg(lap_hr)
        if hr_max is None and lap_hr:
            hr_max = max(lap_hr)
        start_local = _local(lap.start_time, zone)
        pace = _pace(lap.total_time_seconds, lap.distance_meters)
        lines.append(
            " | ".join(
                [
                    _cell(lap.lap_index),
                    start_local.strftime("%H:%M:%S")
                    if start_local
                    else "-",
                    _fmt_duration(lap.total_time_seconds),
                    _cell_km(lap.distance_meters),
                    _fmt_pace(pace),
                    _cell(hr_avg),
                    _cell(hr_max),
                    _cell(_avg(cad)),
                    _cell(_avg(pwr)),
                    _cell(lap.trigger_method),
                ]
            )
        )
    return lines


def _trackpoint_table(
    activity: ParsedActivity,
    density: str,
) -> list[str]:
    """Render the adaptively sampled trackpoint table."""
    short_s, medium_s, long_s = DENSITY_INTERVALS[density]
    lines = [
        (
            f"取樣規則 ({density}): 圈長 <= {SHORT_LAP_SECONDS // 60} 分鐘每"
            f" {short_s} 秒、<= {MEDIUM_LAP_SECONDS // 60} 分鐘每"
            f" {medium_s} 秒、其餘每 {long_s} 秒；每圈首尾必留。"
            "區間配速 = 與上一列之間的平均配速；幾乎沒有前進時標示為暫停。"
        ),
    ]
    timed = [
        tp for tp in activity.trackpoints if tp.timestamp is not None
    ]
    if not timed:
        lines.append("無帶時間戳記的軌跡點。")
        return lines
    origin = _aware(activity.activity.start_time or timed[0].timestamp)
    lap_seconds = {
        lap.lap_index: lap.total_time_seconds for lap in activity.laps
    }

    lines.append(
        "經過 | 圈 | 距離(km) | 區間配速 | 心率 | 步頻 | 功率 | 高度(m)"
    )
    by_lap: dict[int | None, list[Trackpoint]] = defaultdict(list)
    for tp in timed:
        by_lap[tp.lap_index].append(tp)

    for lap_index, points in by_lap.items():
        duration = lap_seconds.get(lap_index)
        if duration is None:
            duration = (
                _aware(points[-1].timestamp) - _aware(points[0].timestamp)
            ).total_seconds()
        interval = _interval_for_lap(duration, short_s, medium_s, long_s)
        previous: Trackpoint | None = None
        for tp in _sample(points, interval):
            elapsed = (_aware(tp.timestamp) - origin).total_seconds()
            altitude = (
                round(tp.altitude_meters, 1)
                if tp.altitude_meters is not None
                else None
            )
            lines.append(
                " | ".join(
                    [
                        _fmt_duration(max(elapsed, 0.0)),
                        _cell(tp.lap_index),
                        _cell_km(tp.distance_meters),
                        _segment_pace(previous, tp),
                        _cell(tp.heart_rate_bpm),
                        _cell(tp.run_cadence_spm),
                        _cell(tp.power_watts),
                        _cell(altitude),
                    ]
                )
            )
            previous = tp
    return lines


def _interval_for_lap(
    lap_seconds: float,
    short_s: int,
    medium_s: int,
    long_s: int,
) -> int:
    """Pick the sampling interval for a lap of the given duration."""
    if lap_seconds <= SHORT_LAP_SECONDS:
        return short_s
    if lap_seconds <= MEDIUM_LAP_SECONDS:
        return medium_s
    return long_s


def _sample(points: list[Trackpoint], interval: int) -> list[Trackpoint]:
    """Keep the first point, one per *interval* seconds, and the last."""
    if not points:
        return []
    kept = [points[0]]
    last_ts = _aware(points[0].timestamp)
    for tp in points[1:-1]:
        ts = _aware(tp.timestamp)
        if (ts - last_ts).total_seconds() >= interval:
            kept.append(tp)
            last_ts = ts
    if len(points) > 1:
        kept.append(points[-1])
    return kept


def _segment_pace(
    previous: Trackpoint | None,
    current: Trackpoint,
) -> str:
    """Average pace between two sampled points, ``-`` when unknown."""
    if (
        previous is None
        or previous.distance_meters is None
        or current.distance_meters is None
    ):
        return "-"
    meters = current.distance_meters - previous.distance_meters
    seconds = (
        _aware(current.timestamp) - _aware(previous.timestamp)
    ).total_seconds()
    if meters <= 0 or seconds <= 0:
        return "-"
    pace = seconds / meters * 1000.0
    if pace > PAUSE_PACE_SECONDS_PER_KM:
        return "暫停"
    return _fmt_pace(pace)


# ---------------------------------------------------------------------------
# Summary sections
# ---------------------------------------------------------------------------


def _totals_lines(activities: list[ParsedActivity]) -> list[str]:
    """Render period-wide totals."""
    stats = _aggregate(activities)
    longest = _longest(activities)
    longest_text = "無資料"
    if longest is not None:
        longest_text = _fmt_km(longest.activity.distance_meters)
    has_cad = any(
        tp.run_cadence_spm is not None
        for item in activities
        for tp in item.trackpoints
    )
    has_pow = any(
        tp.power_watts is not None
        for item in activities
        for tp in item.trackpoints
    )
    return [
        (
            f"跑步次數: {len(activities)}"
            f" | 總距離: {_fmt_km(stats['meters'])}"
            f" | 總時間: {_fmt_duration(stats['seconds'])}"
        ),
        (
            f"平均配速: {_fmt_pace(stats['pace'])} /km"
            f" | 平均心率 (時間加權): {_fmt_int(stats['avg_hr'], 'bpm')}"
            f" | 最高心率: {_fmt_int(stats['max_hr'], 'bpm')}"
        ),
        f"最長單次: {longest_text}",
        (
            f"步頻資料: {'有' if has_cad else '無'}"
            f" | 功率資料: {'有' if has_pow else '無'}"
        ),
    ]


def _weekly_table(
    known: list[tuple[datetime, ParsedActivity]],
) -> list[str]:
    """Render Monday-to-Sunday weekly totals covering the whole range."""
    if not known:
        return ["無可用日期。"]
    by_week: dict[date, list[ParsedActivity]] = defaultdict(list)
    for dt, item in known:
        by_week[_week_start(dt.date())].append(item)
    first = _week_start(known[0][0].date())
    last = _week_start(known[-1][0].date())
    lines = [
        (
            "週 | 起訖 | 次數 | 距離(km) | 時間 | 平均配速 | 平均心率"
            " | 最長單次(km)"
        )
    ]
    current = first
    while current <= last:
        items = by_week.get(current, [])
        stats = _aggregate(items)
        longest = _longest(items)
        iso_year, iso_week, _ = current.isocalendar()
        end = current + timedelta(days=6)
        longest_km = (
            longest.activity.distance_meters
            if longest is not None
            else None
        )
        lines.append(
            " | ".join(
                [
                    f"{iso_year}-W{iso_week:02d}",
                    f"{current.strftime('%m/%d')}~{end.strftime('%m/%d')}",
                    str(len(items)),
                    _cell_km(stats["meters"]) if items else "0",
                    _fmt_duration(stats["seconds"]) if items else "0:00",
                    _fmt_pace(stats["pace"]),
                    _cell(stats["avg_hr"]),
                    _cell_km(longest_km),
                ]
            )
        )
        current += timedelta(days=7)
    return lines


def _daily_table(
    known: list[tuple[datetime, ParsedActivity]],
) -> list[str]:
    """Render totals for each day that has at least one run."""
    if not known:
        return ["無可用日期。"]
    by_day: dict[date, list[ParsedActivity]] = defaultdict(list)
    for dt, item in known:
        by_day[dt.date()].append(item)
    lines = ["日期 | 次數 | 距離(km) | 時間 | 平均配速 | 平均心率"]
    for day in sorted(by_day):
        items = by_day[day]
        stats = _aggregate(items)
        lines.append(
            " | ".join(
                [
                    f"{day.isoformat()} (週{_WEEKDAYS[day.weekday()]})",
                    str(len(items)),
                    _cell_km(stats["meters"]),
                    _fmt_duration(stats["seconds"]),
                    _fmt_pace(stats["pace"]),
                    _cell(stats["avg_hr"]),
                ]
            )
        )
    return lines


def _run_table(
    dated: list[tuple[datetime | None, ParsedActivity]],
) -> list[str]:
    """Render one line per run."""
    if not dated:
        return ["無跑步記錄。"]
    lines = [
        (
            "日期 | 開始 | 距離(km) | 時間 | 配速(/km) | 平均心率 | 最高心率"
            " | 平均步頻 | 平均功率 | 圈數 | 檔案"
        )
    ]
    for dt, item in dated:
        act = item.activity
        cad = _values(item.trackpoints, "run_cadence_spm")
        pwr = _values(item.trackpoints, "power_watts")
        pace = _pace(act.total_time_seconds, act.distance_meters)
        lines.append(
            " | ".join(
                [
                    dt.date().isoformat() if dt else "未知",
                    dt.strftime("%H:%M") if dt else "-",
                    _cell_km(act.distance_meters),
                    _fmt_duration(act.total_time_seconds),
                    _fmt_pace(pace),
                    _cell(act.average_heart_rate_bpm),
                    _cell(act.maximum_heart_rate_bpm),
                    _cell(_avg(cad)),
                    _cell(_avg(pwr)),
                    str(len(item.laps)),
                    Path(item.source.file_name).name,
                ]
            )
        )
    return lines


def _aggregate(activities: list[ParsedActivity]) -> dict:
    """Sum distance/time and compute pace and weighted HR."""
    meters = [
        a.activity.distance_meters
        for a in activities
        if a.activity.distance_meters is not None
    ]
    seconds = [
        a.activity.total_time_seconds
        for a in activities
        if a.activity.total_time_seconds is not None
    ]
    pace_pairs = [
        (a.activity.total_time_seconds, a.activity.distance_meters)
        for a in activities
        if a.activity.total_time_seconds is not None
        and a.activity.distance_meters is not None
        and a.activity.distance_meters > 0
    ]
    hr_pairs = [
        (a.activity.average_heart_rate_bpm, a.activity.total_time_seconds)
        for a in activities
        if a.activity.average_heart_rate_bpm is not None
        and a.activity.total_time_seconds
    ]
    max_hrs = [
        a.activity.maximum_heart_rate_bpm
        for a in activities
        if a.activity.maximum_heart_rate_bpm is not None
    ]
    pace = None
    if pace_pairs:
        pace = _pace(
            sum(s for s, _ in pace_pairs),
            sum(m for _, m in pace_pairs),
        )
    avg_hr = None
    if hr_pairs:
        weight = sum(w for _, w in hr_pairs)
        avg_hr = round(sum(hr * w for hr, w in hr_pairs) / weight)
    return {
        "meters": sum(meters) if meters else None,
        "seconds": sum(seconds) if seconds else None,
        "pace": pace,
        "avg_hr": avg_hr,
        "max_hr": max(max_hrs) if max_hrs else None,
    }


def _longest(activities: list[ParsedActivity]) -> ParsedActivity | None:
    """Return the activity with the greatest distance."""
    with_distance = [
        a for a in activities if a.activity.distance_meters is not None
    ]
    if not with_distance:
        return None
    return max(with_distance, key=lambda a: a.activity.distance_meters)


def _week_start(day: date) -> date:
    """Return the Monday of the week containing *day*."""
    return day - timedelta(days=day.weekday())


# ---------------------------------------------------------------------------
# Naming and formatting helpers
# ---------------------------------------------------------------------------


def _run_file_stem(
    activity: ParsedActivity,
    zone: tzinfo,
    index: int,
) -> str:
    """Build ``<date>_<HHMM>_<km>km`` or a fallback stem."""
    local_start = _local(activity.activity.start_time, zone)
    if local_start is None:
        return f"unknown_start_{index:03d}"
    km = _km(activity.activity.distance_meters)
    km_text = f"{km:.2f}km" if km is not None else "unknown_km"
    return f"{local_start.strftime('%Y-%m-%d_%H%M')}_{km_text}"


def _unique_name(stem: str, used: set[str]) -> str:
    """Return *stem* or a numbered variant that is not in *used*."""
    candidate = stem
    counter = 2
    while candidate in used:
        candidate = f"{stem}_{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def _zone(timezone_name: str) -> tzinfo:
    """Return a ZoneInfo, with fixed-offset fallbacks for known zones."""
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        if timezone_name == "Asia/Taipei":
            return timezone(timedelta(hours=8), timezone_name)
        if timezone_name == "UTC":
            return UTC
        raise ValueError(
            f"Invalid timezone_name: {timezone_name!r}"
        ) from exc


def _aware(value: datetime) -> datetime:
    """Return a UTC-aware datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _local(value: datetime | None, zone: tzinfo) -> datetime | None:
    """Convert to the configured zone, ``None`` stays ``None``."""
    if value is None:
        return None
    return _aware(value).astimezone(zone)


def _sort_key(activity: ParsedActivity) -> tuple[bool, datetime]:
    """Sort by start time with missing start times last."""
    start = activity.activity.start_time
    if start is None:
        return True, datetime.max.replace(tzinfo=UTC)
    return False, _aware(start)


def _values(points: list[Trackpoint], attribute: str) -> list:
    """Collect non-``None`` values of *attribute* from *points*."""
    return [
        getattr(tp, attribute)
        for tp in points
        if getattr(tp, attribute) is not None
    ]


def _date_with_weekday(value: datetime | None) -> str:
    """Format ``YYYY-MM-DD (週X)``."""
    if value is None:
        return "未知日期"
    return f"{value.date().isoformat()} (週{_WEEKDAYS[value.weekday()]})"


def _pace(seconds: float | None, meters: float | None) -> float | None:
    """Seconds per kilometre or ``None``."""
    if seconds is None or meters is None or meters <= 0 or seconds <= 0:
        return None
    return seconds / meters * 1000.0


def _km(meters: float | None) -> float | None:
    """Metres to kilometres rounded to three decimals."""
    if meters is None:
        return None
    return round(meters / 1000.0, 3)


def _avg(values: list) -> int | None:
    """Rounded integer mean or ``None``."""
    if not values:
        return None
    return round(sum(values) / len(values))


def _fmt_duration(seconds: float | None) -> str:
    """Format seconds as ``h:mm:ss`` or ``m:ss``."""
    if seconds is None:
        return "無資料"
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _fmt_pace(pace_seconds_per_km: float | None) -> str:
    """Format pace as ``m:ss``."""
    if pace_seconds_per_km is None:
        return "-"
    total = round(pace_seconds_per_km)
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


def _fmt_km(meters: float | None) -> str:
    """Format metres as ``x.xx km``."""
    km = _km(meters)
    return "無資料" if km is None else f"{km:.2f} km"


def _fmt_int(value: float | None, unit: str) -> str:
    """Format an integer with a unit or ``無資料``."""
    if value is None:
        return "無資料"
    return f"{round(value)} {unit}"


def _fmt_avg(values: list, unit: str = "") -> str:
    """Format the mean of *values* with an optional unit."""
    mean = _avg(values)
    if mean is None:
        return "無資料"
    return f"{mean} {unit}".strip()


def _fmt_max(values: list, unit: str = "") -> str:
    """Format the maximum of *values* with an optional unit."""
    if not values:
        return "無資料"
    return f"{max(values)} {unit}".strip()


def _altitude_line(altitudes: list[float]) -> str:
    """Min/max altitude and positive-delta elevation gain."""
    if not altitudes:
        return "無資料"
    gain_text = "無資料"
    if len(altitudes) >= 2:
        gain = sum(
            later - earlier
            for earlier, later in pairwise(altitudes)
            if later > earlier
        )
        gain_text = f"{gain:.1f} m"
    return (
        f"最低 {min(altitudes):.1f} m | 最高 {max(altitudes):.1f} m"
        f" | 估算爬升 {gain_text}"
    )


def _cell_km(meters: float | None) -> str:
    """Render metres as a two-decimal kilometre cell."""
    km = _km(meters)
    return "-" if km is None else f"{km:.2f}"


def _cell(value: object) -> str:
    """Render a table cell, ``-`` for missing values."""
    if value is None:
        return "-"
    return str(value)


__all__ = [
    "ALL_IN_ONE_FILE_NAME",
    "DENSITY_CHOICES",
    "RUNS_DIR_NAME",
    "SUMMARY_FILE_NAME",
    "AiTextPaths",
    "render_activity_text",
    "render_all_in_one_text",
    "render_summary_text",
    "write_ai_text_outputs",
]
