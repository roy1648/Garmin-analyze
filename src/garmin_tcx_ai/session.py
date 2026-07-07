"""No-inference session bundles for multiple normalized TCX activities."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from garmin_tcx_ai.models import ParsedActivity, Trackpoint
from garmin_tcx_ai.summary import build_ai_summary

SCHEMA_VERSION = "tcx_training_data_v1"


def build_session_bundle(
    activities: list[ParsedActivity],
    max_gap_minutes: int = 30,
    timezone_name: str = "Asia/Taipei",
) -> dict:
    """Build a no-inference session bundle from normalized activities."""
    if max_gap_minutes < 0:
        raise ValueError("max_gap_minutes must be greater than or equal to 0")
    zone = _timezone(timezone_name)

    ordered = sorted(activities, key=_sort_key)
    groups = _group_activities(ordered, max_gap_minutes, zone)
    counters: dict[tuple[str, str], int] = {}
    sessions = [
        _build_session(
            group,
            max_gap_minutes,
            counters,
            zone,
            timezone_name,
        )
        for group in groups
    ]
    missing_start_count = sum(
        item.activity.start_time is None for item in ordered
    )
    warning_count = sum(len(item.warnings) for item in ordered)
    cadence_count = sum(
        point.run_cadence_spm is not None
        for item in ordered
        for point in item.trackpoints
    )
    power_count = sum(
        point.power_watts is not None
        for item in ordered
        for point in item.trackpoints
    )
    policies = sorted({item.privacy.gps_policy for item in ordered})

    quality_notes: list[str] = []
    if missing_start_count:
        quality_notes.append(
            "Activities with missing start_time are separate session "
            "candidates."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "export_scope": {
            "type": "session_bundle",
            "activity_count": len(ordered),
            "session_candidate_count": len(sessions),
            "contains_multiple_activities": len(ordered) > 1,
        },
        "data_policy": {
            "activity_equals_one_tcx_file": True,
            "session_may_contain_multiple_activities": True,
            "grouping_is_candidate_not_fact": True,
            "no_workout_role_inference": True,
            "no_coaching_advice": True,
            "no_medical_interpretation": True,
            "manual_context_fields_are_placeholders": True,
            "allowed_sources": [
                "tcx_raw_fields",
                "fixed_formula_computation",
                "time_gap_grouping_rule",
            ],
        },
        "sessions": sessions,
        "data_quality": {
            "activity_count": len(ordered),
            "activities_missing_start_time_count": missing_start_count,
            "source_warning_count": warning_count,
            "trackpoints_with_run_cadence_count": cadence_count,
            "trackpoints_with_power_count": power_count,
            "notes": quality_notes,
        },
        "privacy": {
            "gps_policies": policies,
            "gps_coordinates_included": False,
            "route_details_included": False,
        },
    }


def render_session_bundle_markdown(bundle: dict) -> str:
    """Render a concise factual Markdown session bundle."""
    scope = bundle["export_scope"]
    policy = bundle["data_policy"]
    quality = bundle["data_quality"]
    privacy = bundle["privacy"]
    lines = [
        "# TCX Multi-Activity Report",
        "# TCX 多活動報告",
        "",
        "This report packages one or more TCX activities for AI-readable "
        "review. It does not merge them into one recorded workout.",
        "本報告封裝一或多個 TCX 活動以供 AI 讀取審閱。這並不代表將它們合併為單次記錄的運動。",
        "",
        "## Data Policy",
        "## 資料政策",
        "",
        "- Session candidates are candidate activity groups for review; "
        "they do not merge activities into one recorded workout.",
        "- Session 候選分組為供審閱的候選活動分組；它們不會將活動合併為單次記錄的運動。",
        "- Session 分組僅為候選分組，而非記錄事實。",
        "- 角色推論已停用。",
        "- 活動角色未推論。",
        f"- 課表／活動角色推論已停用："
        f"{policy['no_workout_role_inference']}",
        "- Manual context fields are placeholders only and were not "
        "inferred from TCX.",
        "- 手動補充資訊欄位僅為預留位置，未從 TCX 推論。",
        "- Cadence values are raw Garmin RunCadence values; no "
        "cadence x2 conversion is applied.",
        "- 步頻值為原始 Garmin RunCadence 值；未套用步頻 2 倍換算。",
        "",
        "## Export Scope",
        "## 輸出範圍",
        "",
        f"- 活動紀錄：{scope['activity_count']}",
        f"- Session 候選分組：{scope['session_candidate_count']}",
        "",
        "## Session Candidates",
        "## Session 候選分組",
        "",
    ]

    if not bundle["sessions"]:
        lines.extend(["無 Session 候選分組。", ""])
    for session in bundle["sessions"]:
        lines.extend(_session_markdown(session))

    lines.extend(["## Activities", "## 活動紀錄", ""])
    for session in bundle["sessions"]:
        for activity in session["activities"]:
            item = activity["activity_summary"]
            lines.extend(
                [
                    f"### {session['session_id']} / 活動 "
                    f"{activity['activity_order']}",
                    "",
                    f"- 來源檔案：{activity['source_file']}",
                    f"- 運動：{_md(item['sport'])}",
                    f"- 開始時間：{_md(item['start_time'])}",
                    f"- 本地開始時間：{_md(item['start_time_local'])}",
                    f"- 本地日期：{_md(item['local_date'])}",
                    f"- 時區：{_md(item['timezone'])}",
                    f"- 時間：{_unit(item['duration_minutes'], 'min')}",
                    f"- 距離：{_unit(item['distance_km'], 'km')}",
                    "- 平均原始跑步步頻："
                    f"{_md(activity['key_metrics']['cadence']['avg_run_cadence_raw'])}",
                    "- 平均功率："
                    f"{_md(activity['key_metrics']['power']['avg_watts'])}",
                    "- 角色：未標記（未推論）",
                    "",
                ]
            )

    lines.extend(["## Lap Summaries", "## Lap 摘要", ""])
    for session in bundle["sessions"]:
        for activity in session["activities"]:
            lines.extend(_laps_markdown(activity))

    lines.extend(["## Computed Split Metrics", "## 固定公式分段指標", ""])
    for session in bundle["sessions"]:
        for activity in session["activities"]:
            lines.extend(_split_markdown(activity))

    lines.extend(
        [
            "## Data Quality",
            "## 資料品質",
            "",
            f"- 來源警告：{quality['source_warning_count']}",
            "- 活動缺少開始時間："
            f"{quality['activities_missing_start_time_count']}",
            "- Trackpoint 具備跑步步頻："
            f"{quality['trackpoints_with_run_cadence_count']}",
            "- Trackpoint 具備功率："
            f"{quality['trackpoints_with_power_count']}",
        ]
    )
    lines.extend(f"- {_translate_note(note)}" for note in quality["notes"])
    lines.extend(
        [
            "",
            "## Privacy",
            "## 隱私保護",
            "",
            f"- GPS 政策：{', '.join(_translate_value(p) for p in privacy['gps_policies']) or '無'}",
            "- 不包含 GPS 座標。",
            "- 不包含路線細節。",
            "",
        ]
    )
    return "\n".join(lines)


def _group_activities(
    activities: list[ParsedActivity],
    max_gap_minutes: int,
    zone: tzinfo,
) -> list[list[ParsedActivity]]:
    """Group adjacent activities using local date, sport, and start gap."""
    groups: list[list[ParsedActivity]] = []
    max_gap = timedelta(minutes=max_gap_minutes)
    for item in activities:
        start = item.activity.start_time
        if not groups or start is None:
            groups.append([item])
            continue
        previous = groups[-1][-1]
        previous_start = previous.activity.start_time
        same_local_date = (
            previous_start is not None
            and _local_date(previous_start, zone) == _local_date(start, zone)
        )
        same_sport = previous.activity.sport == item.activity.sport
        within_gap = (
            previous_start is not None
            and _aware(start) - _aware(previous_start) <= max_gap
        )
        if same_local_date and same_sport and within_gap:
            groups[-1].append(item)
        else:
            groups.append([item])
    return groups


def _build_session(
    activities: list[ParsedActivity],
    max_gap_minutes: int,
    counters: dict[tuple[str, str], int],
    zone: tzinfo,
    timezone_name: str,
) -> dict:
    """Build one session-candidate payload."""
    first = activities[0]
    start = first.activity.start_time
    date_text = _local_date(start, zone) or "unknown_date"
    sport = first.activity.sport or "Unknown"
    counter_key = (date_text, sport)
    counters[counter_key] = counters.get(counter_key, 0) + 1
    session_id = (
        f"{date_text}_{_identifier(sport)}_{counters[counter_key]:03d}"
    )
    entries = []
    for order, item in enumerate(activities, start=1):
        entry = build_ai_summary(item, timezone_name)
        entry.update(
            {
                "activity_order": order,
                "source_file": Path(item.source.file_name).name,
                "role": None,
                "role_source": "not_inferred",
            }
        )
        entries.append(entry)

    missing_start = sum(
        item.activity.start_time is None for item in activities
    )
    notes: list[str] = []
    if missing_start:
        notes.append(
            "Missing start_time prevents grouping with other activities."
        )
    if any(item.activity.distance_meters is None for item in activities):
        notes.append("At least one activity has missing distance data.")
    if any(
        item.activity.total_time_seconds is None for item in activities
    ):
        notes.append("At least one activity has missing duration data.")

    session_start = _minimum_start(activities)
    session_end = _maximum_end(activities)
    all_trackpoints = [
        point for item in activities for point in item.trackpoints
    ]
    return {
        "session_id": session_id,
        "grouping_source": (
            "missing_start_time_singleton"
            if missing_start
            else "time_gap_rule"
        ),
        "grouping_confidence": "candidate",
        "grouping_rule": {
            "same_local_date": True,
            "timezone": timezone_name,
            "same_sport": True,
            "max_gap_minutes": max_gap_minutes,
        },
        "role_inference": "disabled",
        "activity_count": len(activities),
        "start_time": _iso(session_start),
        "end_time": _iso(session_end),
        "start_time_local": _local_iso(session_start, zone),
        "end_time_local": _local_iso(session_end, zone),
        "timezone": timezone_name,
        "local_date": _local_date(session_start, zone),
        "total_distance_km": _sum_km(
            item.activity.distance_meters for item in activities
        ),
        "total_duration_minutes": _sum_minutes(
            item.activity.total_time_seconds for item in activities
        ),
        "weighted_average_heart_rate_bpm": _weighted_hr(activities),
        "maximum_heart_rate_bpm": _maximum_hr(activities),
        "cadence": _cadence_metrics(all_trackpoints),
        "power": _power_metrics(all_trackpoints),
        "manual_context": _manual_context(),
        "activities": entries,
        "data_quality": {
            "activities_missing_start_time_count": missing_start,
            "trackpoints_with_run_cadence_count": sum(
                point.run_cadence_spm is not None
                for point in all_trackpoints
            ),
            "trackpoints_with_power_count": sum(
                point.power_watts is not None
                for point in all_trackpoints
            ),
            "notes": notes,
        },
    }


def _sort_key(activity: ParsedActivity) -> tuple[bool, datetime]:
    """Sort known start times first and missing start times last."""
    start = activity.activity.start_time
    if start is not None and start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start is None, start or datetime.max.replace(tzinfo=timezone.utc)


def _minimum_start(activities: list[ParsedActivity]) -> datetime | None:
    """Return the earliest known start time."""
    starts = [
        item.activity.start_time
        for item in activities
        if item.activity.start_time is not None
    ]
    return min(starts, key=_aware) if starts else None


def _maximum_end(activities: list[ParsedActivity]) -> datetime | None:
    """Return the latest fixed-formula activity end time."""
    ends = []
    for item in activities:
        start = item.activity.start_time
        if start is None:
            continue
        duration = item.activity.total_time_seconds
        ends.append(start + timedelta(seconds=duration or 0.0))
    return max(ends, key=_aware) if ends else None


def _sum_km(values: Iterable[float | None]) -> float | None:
    """Sum available meter values and return kilometers."""
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / 1000.0, 3)


def _sum_minutes(values: Iterable[float | None]) -> float | None:
    """Sum available second values and return minutes."""
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / 60.0, 2)


def _weighted_hr(activities: list[ParsedActivity]) -> float | None:
    """Compute duration-weighted average activity heart rate."""
    pairs = [
        (
            item.activity.average_heart_rate_bpm,
            item.activity.total_time_seconds,
        )
        for item in activities
        if item.activity.average_heart_rate_bpm is not None
        and item.activity.total_time_seconds is not None
        and item.activity.total_time_seconds > 0
    ]
    total_weight = sum(duration for _, duration in pairs)
    if total_weight <= 0:
        return None
    weighted = sum(hr * duration for hr, duration in pairs)
    return round(weighted / total_weight, 1)


def _maximum_hr(activities: list[ParsedActivity]) -> int | None:
    """Return the highest available activity maximum heart rate."""
    values = [
        item.activity.maximum_heart_rate_bpm
        for item in activities
        if item.activity.maximum_heart_rate_bpm is not None
    ]
    return max(values) if values else None


def _cadence_metrics(trackpoints: list[Trackpoint]) -> dict:
    """Aggregate raw run-cadence samples across a session candidate."""
    values = [
        point.run_cadence_spm
        for point in trackpoints
        if point.run_cadence_spm is not None
    ]
    return {
        "avg_run_cadence_raw": _average(values),
        "max_run_cadence_raw": max(values) if values else None,
        "trackpoints_with_run_cadence_count": len(values),
        "source": "activity_trackpoint_aggregate",
        "avg_cadence_spm": None,
        "conversion_rule": None,
    }


def _power_metrics(trackpoints: list[Trackpoint]) -> dict:
    """Aggregate raw power samples across a session candidate."""
    values = [
        point.power_watts
        for point in trackpoints
        if point.power_watts is not None
    ]
    return {
        "avg_watts": _average(values),
        "max_watts": max(values) if values else None,
        "trackpoints_with_power_count": len(values),
        "source": "activity_trackpoint_aggregate",
    }


def _average(values: list[int]) -> float | None:
    """Return a one-decimal arithmetic mean for integer samples."""
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def _manual_context() -> dict:
    """Return empty manual-only context placeholders."""
    return {
        "planned_workout_text": None,
        "planned_workout_source": "manual_only",
        "completion": None,
        "rpe_1_to_10": None,
        "pain_before": None,
        "pain_during": None,
        "pain_after": None,
        "next_day_status": None,
    }


def _timezone(timezone_name: str) -> tzinfo:
    """Return a ZoneInfo instance or raise ValueError for an invalid name."""
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        fallback = _timezone_fallback(timezone_name)
        if fallback is not None:
            return fallback
        raise ValueError(
            f"Invalid timezone_name: {timezone_name!r}"
        ) from exc


def _timezone_fallback(timezone_name: str) -> tzinfo | None:
    """Return stdlib fixed-offset fallbacks for known stable zones."""
    if timezone_name == "Asia/Taipei":
        return timezone(timedelta(hours=8), timezone_name)
    if timezone_name == "UTC":
        return timezone.utc
    return None


def _local_date(value: datetime | None, zone: tzinfo) -> str | None:
    """Return the deterministic local date for a recorded timestamp."""
    local = _local_datetime(value, zone)
    return local.date().isoformat() if local else None


def _local_iso(value: datetime | None, zone: tzinfo) -> str | None:
    """Return an ISO timestamp converted to the configured timezone."""
    local = _local_datetime(value, zone)
    return local.isoformat() if local else None


def _local_datetime(
    value: datetime | None,
    zone: tzinfo,
) -> datetime | None:
    """Convert a recorded timestamp to the configured timezone."""
    if value is None:
        return None
    return _aware(value).astimezone(zone)


def _iso(value: datetime | None) -> str | None:
    """Serialize a datetime as UTC ISO 8601 with a Z suffix."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _translate_value(val: object) -> str:
    """Translate value strings to Traditional Chinese (Taiwan) for Markdown rendering."""
    if val is None:
        return "無資料"
    val_str = str(val)
    translations = {
        "unavailable": "無資料",
        "unavailable (not inferred)": "未標記（未推論）",
        "placeholders only; not inferred": "僅為手動填寫欄位，未從 TCX 推論",
        "Running": "跑步",
        "running": "跑步",
        "Other": "其他",
        "other": "其他",
        "candidate": "候選",
        "time_gap_rule": "時間間隔規則",
        "missing_start_time_singleton": "缺少開始時間單一活動",
        "disabled": "已停用",
        "not_inferred": "未推論",
        "invalid": "無效",
        "low": "低",
        "medium": "中",
        "high": "高",
        "missing_distance_or_duration": "缺少距離或時間資料",
        "non_positive_distance_or_duration": "距離或時間資料非正數",
        "lap_distance_below_0.1km": "Lap 距離低於 0.1km",
        "lap_distance_between_0.1km_and_0.3km": "Lap 距離介於 0.1km 至 0.3km",
        "lap_distance_at_least_0.3km": "Lap 距離至少 0.3km",
        "split_at_cumulative_distance_midpoint": "固定累計距離中點分段",
        "computed_metrics_only_no_training_interpretation": "僅計算指標不進行訓練解讀",
        "limited_for_interval_or_mixed_lap_activity": "間歇或混合 Lap 活動受限",
        "redact_start_end": "遮蔽起點與終點",
        "redact_all": "完全遮蔽",
        "keep": "保留",
        "none": "無",
    }
    return translations.get(val_str, val_str)


def _translate_note(note: str) -> str:
    """Translate data quality or split notes to Traditional Chinese (Taiwan) for Markdown."""
    translations = {
        "This split metric is a fixed-formula summary and must not be interpreted as fatigue, workout quality, or workout type.":
            "本分段指標僅為固定公式摘要，不得解讀為疲勞度、訓練品質或訓練類型。",
        "Distance data is missing or insufficient for the fixed cumulative-distance midpoint split.":
            "距離資料缺失或不足，無法計算固定累計距離中點分段。",
        "Timestamp or distance data is missing or insufficient for half-split pace.":
            "時間戳記或距離資料缺失或不足，無法計算後半段平均配速。",
        "Heart rate data is missing or insufficient in at least one half.":
            "至少有一半的區段心率資料缺失或不足。",
        "No trackpoints are available.":
            "無 trackpoint 軌跡點資料。",
        "Fewer than two altitude readings; elevation gain cannot be estimated.":
            "高度讀數少於兩個，無法估算爬升高度。",
        "Some key fields are missing; see missing_key_fields.":
            "部分關鍵欄位缺失，請參閱 missing_key_fields。",
        "Activities with missing start_time are separate session candidates.":
            "缺少 start_time 的活動將作為獨立的 Session 候選分組。",
        "Missing start_time prevents grouping with other activities.":
            "缺少 start_time，無法與其他活動進行分組。",
        "At least one activity has missing distance data.":
            "至少有一個活動缺少距離資料。",
        "At least one activity has missing duration data.":
            "至少有一個活動缺少時間資料。",
    }
    return translations.get(note, note)


def _aware(value: datetime) -> datetime:
    """Return a timezone-aware datetime for safe comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _identifier(value: str) -> str:
    """Return a stable identifier component without path punctuation."""
    result = "".join(char if char.isalnum() else "_" for char in value)
    return result.strip("_") or "Unknown"


def _session_markdown(session: dict) -> list[str]:
    """Render one session candidate summary."""
    return [
        f"### {session['session_id']}",
        "",
        f"- 分組信心標記：{_translate_value(session['grouping_confidence'])}",
        f"- 分組來源：{_translate_value(session['grouping_source'])}",
        f"- 角色推論：{_translate_value(session['role_inference'])}",
        f"- 活動紀錄：{session['activity_count']}",
        f"- 開始時間：{_md(session['start_time'])}",
        f"- 結束時間：{_md(session['end_time'])}",
        f"- 本地日期：{_md(session['local_date'])}",
        f"- 時區：{_md(session['timezone'])}",
        f"- 總距離：{_unit(session['total_distance_km'], 'km')}",
        "- 總時間: "
        f"{_unit(session['total_duration_minutes'], 'min')}",
        "- 加權平均心率: "
        f"{_unit(session['weighted_average_heart_rate_bpm'], 'bpm')}",
        "- 最高心率: "
        f"{_unit(session['maximum_heart_rate_bpm'], 'bpm')}",
        "- 平均原始跑步步頻: "
        f"{_md(session['cadence']['avg_run_cadence_raw'])}",
        f"- 平均功率：{_md(session['power']['avg_watts'])}",
        "- 手動補充資訊欄位：僅為手動填寫欄位，未從 TCX 推論。",
        "",
    ]


def _laps_markdown(activity: dict) -> list[str]:
    """Render factual lap rows for one activity."""
    title = (
        f"### {activity['source_file']} / Laps"
    )
    lines = [title, ""]
    if not activity["lap_summary"]:
        return [*lines, "無 Lap 資料。", ""]
    lines.extend(
        [
            "| Lap | 時間 (min) | 距離 (km) | 配速 "
            "| 配速可信度 | 可信度原因 | 平均原始步頻 "
            "| 平均功率 | 角色 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for lap in activity["lap_summary"]:
        lines.append(
            f"| {_md(lap['lap_index'])} "
            f"| {_md(lap['duration_minutes'])} "
            f"| {_md(lap['distance_km'])} "
            f"| {_md(lap['average_pace_formatted'])} "
            f"| {_md(lap['pace_reliability'])} "
            f"| {_md(lap['reliability_reason'])} "
            f"| {_md(lap['cadence']['avg_run_cadence_raw'])} "
            f"| {_md(lap['power']['avg_watts'])} "
            "| 未標記（未推論） |"
        )
    lines.append("")
    return lines


def _split_markdown(activity: dict) -> list[str]:
    """Render neutral split metrics for one activity."""
    split = activity["computed_split_metrics"]
    lines = [
        f"### {activity['source_file']} / 固定公式分段指標",
        "",
        f"- 方法：{_md(split['method'])}",
        f"- 解讀層級：{_md(split['interpretation_level'])}",
        "- 前半段平均配速："
        f"{_unit(split['first_half_average_pace_seconds_per_km'], 's/km')}",
        "- 後半段平均配速："
        f"{_unit(split['second_half_average_pace_seconds_per_km'], 's/km')}",
        "- 配速後半段差異："
        f"{_unit(split['pace_second_half_delta_seconds_per_km'], 's/km')}",
        "- 心率後半段差異："
        f"{_unit(split['heart_rate_second_half_delta_bpm'], 'bpm')}",
    ]
    lines.extend(f"- 備註：{_translate_note(note)}" for note in split["notes"])
    lines.append("")
    return lines


def _md(value: object) -> str:
    """Render missing values consistently for Markdown."""
    if value is None:
        return "無資料"
    return _translate_value(value)


def _unit(value: object, unit: str) -> str:
    """Render a value with a unit or as unavailable."""
    if value is None:
        return "無資料"
    return f"{value} {unit}"
