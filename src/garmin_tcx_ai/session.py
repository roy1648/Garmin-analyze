"""No-inference session bundles for multiple normalized TCX activities."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from garmin_tcx_ai.models import ParsedActivity
from garmin_tcx_ai.summary import build_ai_summary

SCHEMA_VERSION = "tcx_training_data_v1"


def build_session_bundle(
    activities: list[ParsedActivity],
    max_gap_minutes: int = 30,
) -> dict:
    """Build a no-inference session bundle from normalized activities."""
    if max_gap_minutes < 0:
        raise ValueError("max_gap_minutes must be greater than or equal to 0")

    ordered = sorted(activities, key=_sort_key)
    groups = _group_activities(ordered, max_gap_minutes)
    counters: dict[tuple[str, str], int] = {}
    sessions = [
        _build_session(group, max_gap_minutes, counters)
        for group in groups
    ]
    missing_start_count = sum(
        item.activity.start_time is None for item in ordered
    )
    warning_count = sum(len(item.warnings) for item in ordered)
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
        "# TCX Session Bundle",
        "",
        "## Data Policy",
        "",
        "- Session grouping is a candidate, not a recorded fact.",
        "- Role inference is disabled.",
        "- Activity role is not inferred.",
        f"- Workout role inference disabled: "
        f"{policy['no_workout_role_inference']}",
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
                    f"- Duration: {_unit(item['duration_minutes'], 'min')}",
                    f"- Distance: {_unit(item['distance_km'], 'km')}",
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
    activities: list[ParsedActivity], max_gap_minutes: int
) -> list[list[ParsedActivity]]:
    """Group adjacent activities using only date, sport, and start gap."""
    groups: list[list[ParsedActivity]] = []
    max_gap = timedelta(minutes=max_gap_minutes)
    for item in activities:
        start = item.activity.start_time
        if not groups or start is None:
            groups.append([item])
            continue
        previous = groups[-1][-1]
        previous_start = previous.activity.start_time
        same_date = (
            previous_start is not None
            and previous_start.date() == start.date()
        )
        same_sport = previous.activity.sport == item.activity.sport
        within_gap = (
            previous_start is not None
            and _aware(start) - _aware(previous_start) <= max_gap
        )
        if same_date and same_sport and within_gap:
            groups[-1].append(item)
        else:
            groups.append([item])
    return groups


def _build_session(
    activities: list[ParsedActivity],
    max_gap_minutes: int,
    counters: dict[tuple[str, str], int],
) -> dict:
    """Build one session-candidate payload."""
    first = activities[0]
    start = first.activity.start_time
    date_text = start.date().isoformat() if start else "unknown_date"
    sport = first.activity.sport or "Unknown"
    counter_key = (date_text, sport)
    counters[counter_key] = counters.get(counter_key, 0) + 1
    session_id = (
        f"{date_text}_{_identifier(sport)}_{counters[counter_key]:03d}"
    )
    entries = []
    for order, item in enumerate(activities, start=1):
        entry = build_ai_summary(item)
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
            "same_sport": True,
            "max_gap_minutes": max_gap_minutes,
        },
        "role_inference": "disabled",
        "activity_count": len(activities),
        "start_time": _iso(_minimum_start(activities)),
        "end_time": _iso(_maximum_end(activities)),
        "total_distance_km": _sum_km(
            item.activity.distance_meters for item in activities
        ),
        "total_duration_minutes": _sum_minutes(
            item.activity.total_time_seconds for item in activities
        ),
        "weighted_average_heart_rate_bpm": _weighted_hr(activities),
        "maximum_heart_rate_bpm": _maximum_hr(activities),
        "activities": entries,
        "data_quality": {
            "activities_missing_start_time_count": missing_start,
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
        f"- Total distance: {_unit(session['total_distance_km'], 'km')}",
        "- Total duration: "
        f"{_unit(session['total_duration_minutes'], 'min')}",
        "- Weighted average heart rate: "
        f"{_unit(session['weighted_average_heart_rate_bpm'], 'bpm')}",
        "- Maximum heart rate: "
        f"{_unit(session['maximum_heart_rate_bpm'], 'bpm')}",
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
            "| Lap | Duration (min) | Distance (km) | Pace | Role |",
            "|---|---|---|---|---|",
        ]
    )
    for lap in activity["lap_summary"]:
        lines.append(
            f"| {_md(lap['lap_index'])} "
            f"| {_md(lap['duration_minutes'])} "
            f"| {_md(lap['distance_km'])} "
            f"| {_md(lap['average_pace_formatted'])} "
            "| unavailable (not inferred) |"
        )
    lines.append("")
    return lines


def _split_markdown(activity: dict) -> list[str]:
    """Render neutral split metrics for one activity."""
    split = activity["computed_split_metrics"]
    return [
        f"### {activity['source_file']} / Split Metrics",
        "",
        f"- Method: {split['method']}",
        "- First half average pace: "
        f"{_unit(split['first_half_average_pace_seconds_per_km'], 's/km')}",
        "- Second half average pace: "
        f"{_unit(split['second_half_average_pace_seconds_per_km'], 's/km')}",
        "- Pace second-half delta: "
        f"{_unit(split['pace_second_half_delta_seconds_per_km'], 's/km')}",
        "- Heart-rate second-half delta: "
        f"{_unit(split['heart_rate_second_half_delta_bpm'], 'bpm')}",
        "",
    ]


def _md(value: object) -> str:
    """Render missing values consistently for Markdown."""
    return "unavailable" if value is None else str(value)


def _unit(value: object, unit: str) -> str:
    """Render a value with a unit or as unavailable."""
    return "unavailable" if value is None else f"{value} {unit}"
