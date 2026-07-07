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
        "",
        "This report packages one or more TCX activities for AI-readable "
        "review. It does not merge them into one recorded workout.",
        "",
        "## Data Policy",
        "",
        "- Session grouping is a candidate, not a recorded fact.",
        "- Session candidates are candidate activity groups for review; "
        "they do not merge activities into one recorded workout.",
        "- Role inference is disabled.",
        "- Activity role is not inferred.",
        f"- Workout role inference disabled: "
        f"{policy['no_workout_role_inference']}",
        "- Manual context fields are placeholders only and were not "
        "inferred from TCX.",
        "- Cadence values are raw Garmin RunCadence values; no cadence "
        "x2 conversion is applied.",
        "",
        "## Export Scope",
        "",
        f"- Activities: {scope['activity_count']}",
        f"- Session candidates: {scope['session_candidate_count']}",
        "",
        "## Session Candidates",
        "",
    ]

    if not bundle["sessions"]:
        lines.extend(["No session candidates are available.", ""])
    for session in bundle["sessions"]:
        lines.extend(_session_markdown(session))

    lines.extend(["## Activities", ""])
    for session in bundle["sessions"]:
        for activity in session["activities"]:
            item = activity["activity_summary"]
            lines.extend(
                [
                    f"### {session['session_id']} / Activity "
                    f"{activity['activity_order']}",
                    "",
                    f"- Source file: {activity['source_file']}",
                    f"- Sport: {_md(item['sport'])}",
                    f"- Start time: {_md(item['start_time'])}",
                    f"- Local start time: {_md(item['start_time_local'])}",
                    f"- Local date: {_md(item['local_date'])}",
                    f"- Timezone: {_md(item['timezone'])}",
                    f"- Duration: {_unit(item['duration_minutes'], 'min')}",
                    f"- Distance: {_unit(item['distance_km'], 'km')}",
                    "- Average run cadence raw: "
                    f"{_md(activity['key_metrics']['cadence']['avg_run_cadence_raw'])}",
                    "- Average watts: "
                    f"{_md(activity['key_metrics']['power']['avg_watts'])}",
                    "- Role: unavailable (not inferred)",
                    "",
                ]
            )

    lines.extend(["## Lap Summaries", ""])
    for session in bundle["sessions"]:
        for activity in session["activities"]:
            lines.extend(_laps_markdown(activity))

    lines.extend(["## Computed Split Metrics", ""])
    for session in bundle["sessions"]:
        for activity in session["activities"]:
            lines.extend(_split_markdown(activity))

    lines.extend(
        [
            "## Data Quality",
            "",
            f"- Source warnings: {quality['source_warning_count']}",
            "- Activities missing start time: "
            f"{quality['activities_missing_start_time_count']}",
            "- Trackpoints with run cadence: "
            f"{quality['trackpoints_with_run_cadence_count']}",
            "- Trackpoints with power: "
            f"{quality['trackpoints_with_power_count']}",
        ]
    )
    lines.extend(f"- {note}" for note in quality["notes"])
    lines.extend(
        [
            "",
            "## Privacy",
            "",
            f"- GPS policies: {', '.join(privacy['gps_policies']) or 'none'}",
            "- GPS coordinates are not included.",
            "- Route details are not included.",
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
        f"- Grouping confidence: {session['grouping_confidence']}",
        f"- Grouping source: {session['grouping_source']}",
        f"- Role inference: {session['role_inference']}",
        f"- Activities: {session['activity_count']}",
        f"- Start time: {_md(session['start_time'])}",
        f"- End time: {_md(session['end_time'])}",
        f"- Local date: {_md(session['local_date'])}",
        f"- Timezone: {_md(session['timezone'])}",
        f"- Total distance: {_unit(session['total_distance_km'], 'km')}",
        "- Total duration: "
        f"{_unit(session['total_duration_minutes'], 'min')}",
        "- Weighted average heart rate: "
        f"{_unit(session['weighted_average_heart_rate_bpm'], 'bpm')}",
        "- Maximum heart rate: "
        f"{_unit(session['maximum_heart_rate_bpm'], 'bpm')}",
        "- Average run cadence raw: "
        f"{_md(session['cadence']['avg_run_cadence_raw'])}",
        f"- Average watts: {_md(session['power']['avg_watts'])}",
        "- Manual context fields: placeholders only; not inferred.",
        "",
    ]


def _laps_markdown(activity: dict) -> list[str]:
    """Render factual lap rows for one activity."""
    title = (
        f"### {activity['source_file']} / Laps"
    )
    lines = [title, ""]
    if not activity["lap_summary"]:
        return [*lines, "No lap data is available.", ""]
    lines.extend(
        [
            "| Lap | Duration (min) | Distance (km) | Pace "
            "| Pace reliability | Reliability reason | Avg cadence raw "
            "| Avg watts | Role |",
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
            "| unavailable (not inferred) |"
        )
    lines.append("")
    return lines


def _split_markdown(activity: dict) -> list[str]:
    """Render neutral split metrics for one activity."""
    split = activity["computed_split_metrics"]
    lines = [
        f"### {activity['source_file']} / Split Metrics",
        "",
        f"- Method: {split['method']}",
        f"- Interpretation level: {split['interpretation_level']}",
        "- First half average pace: "
        f"{_unit(split['first_half_average_pace_seconds_per_km'], 's/km')}",
        "- Second half average pace: "
        f"{_unit(split['second_half_average_pace_seconds_per_km'], 's/km')}",
        "- Pace second-half delta: "
        f"{_unit(split['pace_second_half_delta_seconds_per_km'], 's/km')}",
        "- Heart-rate second-half delta: "
        f"{_unit(split['heart_rate_second_half_delta_bpm'], 'bpm')}",
    ]
    lines.extend(f"- Note: {note}" for note in split["notes"])
    lines.append("")
    return lines


def _md(value: object) -> str:
    """Render missing values consistently for Markdown."""
    return "unavailable" if value is None else str(value)


def _unit(value: object, unit: str) -> str:
    """Render a value with a unit or as unavailable."""
    return "unavailable" if value is None else f"{value} {unit}"
