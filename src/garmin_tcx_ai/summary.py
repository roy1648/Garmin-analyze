"""AI-ready factual summary builder for normalized activities.

This module turns a normalized :class:`ParsedActivity` into the
``ai_summary.json`` payload defined in ``docs/02_data_contract.md`` and
renders the matching ``ai_summary.md`` text. The summary is strictly
factual: it never includes GPS coordinates or route details and it does
not produce coaching or medical interpretation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from garmin_tcx_ai.models import Lap, ParsedActivity, Trackpoint

# Relative pace / heart-rate change required to leave the "stable" label.
TREND_THRESHOLD = 0.03

# Allowed trend labels (see docs/02_data_contract.md section 5.2).
TREND_FASTER_LATER = "faster_later"
TREND_SLOWER_LATER = "slower_later"
TREND_STABLE = "stable"
TREND_INSUFFICIENT = "insufficient_data"

_TREND_METHOD = (
    "Halves are split at the cumulative-distance midpoint. A half must "
    "be more than 3% faster (pace) or higher (heart rate) than the "
    "other to leave 'stable'. Fields are 'insufficient_data' when the "
    "required distance, timestamp, or heart rate data is missing."
)

_SUGGESTED_QUESTIONS = [
    "How consistent was the pacing across the activity, and where "
    "did the largest pace changes occur?",
    "Is there evidence of heart rate drift between the first and "
    "second half at a similar pace?",
    "How consistent are the lap paces, durations, and heart rates "
    "compared with each other?",
    "Do the data quality notes (missing fields or warnings) reduce "
    "confidence in any of the reported metrics?",
]


def build_ai_summary(activity: ParsedActivity) -> dict:
    """Build an AI-ready factual summary for a normalized Running
    activity.

    Returns a JSON-serializable dict with the top-level keys
    ``activity_summary``, ``key_metrics``, ``lap_summary``,
    ``trend_summary``, ``privacy``, ``data_quality`` and ``ai_context``.
    Missing values are ``None`` and datetimes are ISO 8601 strings. GPS
    coordinates and route details are never included.
    """
    activity_summary = _activity_summary(activity)
    key_metrics = _key_metrics(activity)
    lap_summary = [_lap_entry(lap) for lap in activity.laps]
    trend_summary = _trend_summary(activity)
    privacy = _privacy_summary(activity)
    data_quality = _data_quality(activity)
    ai_context = _ai_context(
        activity_summary, key_metrics, trend_summary, privacy
    )
    return {
        "activity_summary": activity_summary,
        "key_metrics": key_metrics,
        "lap_summary": lap_summary,
        "trend_summary": trend_summary,
        "privacy": privacy,
        "data_quality": data_quality,
        "ai_context": ai_context,
    }


def render_ai_summary_markdown(summary: dict) -> str:
    """Render an ``ai_summary.md`` document from a summary dict.

    *summary* must be the dict produced by :func:`build_ai_summary`.
    The output is concise, factual, and never contains GPS coordinates,
    route details, coaching advice, or medical interpretation. Missing
    values are shown as ``unavailable``.
    """
    act = summary["activity_summary"]
    metrics = summary["key_metrics"]
    trend = summary["trend_summary"]
    privacy = summary["privacy"]
    quality = summary["data_quality"]

    lines: list[str] = ["# Running Activity Summary", ""]

    lines += ["## Activity", ""]
    lines += [
        f"- Sport: {_md(act['sport'])}",
        f"- Activity ID: {_md(act['activity_id'])}",
        f"- Start time: {_md(act['start_time'])}",
        f"- Duration: {_md_unit(act['duration_minutes'], 'minutes')}",
        f"- Distance: {_md_unit(act['distance_km'], 'km')}",
        f"- Laps: {_md(act['lap_count'])}",
        f"- Trackpoints: {_md(act['trackpoint_count'])}",
        "",
    ]

    lines += ["## Key Metrics", ""]
    lines += [
        "- Average pace: "
        f"{_md(metrics['average_pace_formatted'])}",
        "- Average heart rate: "
        f"{_md_unit(metrics['average_heart_rate_bpm'], 'bpm')}",
        "- Maximum heart rate: "
        f"{_md_unit(metrics['maximum_heart_rate_bpm'], 'bpm')}",
        "- Maximum speed: "
        f"{_md_unit(metrics['maximum_speed_mps'], 'm/s')}",
        "",
    ]

    lines += ["## Lap Summary", ""]
    lines += _lap_table(summary["lap_summary"])
    lines.append("")

    lines += ["## Pace Trend", ""]
    lines += [
        f"- Trend: {trend['pace_trend']}",
        "- First half average pace: "
        f"{_md_pace(trend['first_half_average_pace_seconds_per_km'])}",
        "- Second half average pace: "
        f"{_md_pace(trend['second_half_average_pace_seconds_per_km'])}",
        f"- Method: {trend['method']}",
        "",
    ]

    lines += ["## Heart Rate Trend", ""]
    lines += [
        f"- Trend: {trend['heart_rate_trend']}",
        "- First half average heart rate: "
        f"{_md_unit(trend['first_half_average_heart_rate_bpm'], 'bpm')}",
        "- Second half average heart rate: "
        f"{_md_unit(trend['second_half_average_heart_rate_bpm'], 'bpm')}",
        "",
    ]

    lines += ["## Elevation", ""]
    lines += [
        "- Minimum altitude: "
        f"{_md_unit(metrics['min_altitude_meters'], 'm')}",
        "- Maximum altitude: "
        f"{_md_unit(metrics['max_altitude_meters'], 'm')}",
        "- Estimated elevation gain: "
        f"{_md_unit(metrics['estimated_elevation_gain_meters'], 'm')}",
        "",
    ]

    lines += ["## Data Quality Notes", ""]
    lines.append(f"- Warnings: {quality['warnings_count']}")
    if quality["warning_codes"]:
        codes = ", ".join(quality["warning_codes"])
        lines.append(f"- Warning codes: {codes}")
    if quality["missing_key_fields"]:
        missing = ", ".join(quality["missing_key_fields"])
        lines.append(f"- Missing key fields: {missing}")
    lines.append(
        f"- Trackpoints: {quality['trackpoints_count']} total, "
        f"{quality['trackpoints_with_heart_rate_count']} with heart "
        f"rate, {quality['trackpoints_with_distance_count']} with "
        f"distance, {quality['trackpoints_with_altitude_count']} with "
        f"altitude, {quality['trackpoints_with_speed_count']} with "
        "speed."
    )
    for note in quality["notes"]:
        lines.append(f"- {note}")
    lines.append("")

    lines += ["## Privacy Notes", ""]
    lines += [
        f"- GPS policy: {privacy['gps_policy']}",
        "- GPS coordinates are not included in this summary.",
        "- Route details are not included in this summary.",
        "",
    ]

    lines += ["## Suggested AI Analysis Questions", ""]
    lines += [f"- {q}" for q in _SUGGESTED_QUESTIONS]
    lines.append("")

    return "\n".join(lines)


# --- section builders -------------------------------------------------


def _activity_summary(parsed: ParsedActivity) -> dict:
    """Build the ``activity_summary`` section."""
    activity = parsed.activity
    return {
        "sport": activity.sport,
        "activity_id": activity.activity_id,
        "start_time": _iso(activity.start_time),
        "duration_minutes": _minutes(activity.total_time_seconds),
        "distance_km": _km(activity.distance_meters),
        "lap_count": len(parsed.laps),
        "trackpoint_count": len(parsed.trackpoints),
    }


def _key_metrics(parsed: ParsedActivity) -> dict:
    """Build the ``key_metrics`` section."""
    activity = parsed.activity
    pace = _pace_seconds_per_km(
        activity.total_time_seconds, activity.distance_meters
    )
    min_alt, max_alt, gain = _altitude_stats(parsed.trackpoints)
    return {
        "duration_minutes": _minutes(activity.total_time_seconds),
        "distance_km": _km(activity.distance_meters),
        "average_pace_seconds_per_km": _round1(pace),
        "average_pace_formatted": _format_pace(pace),
        "average_heart_rate_bpm": activity.average_heart_rate_bpm,
        "maximum_heart_rate_bpm": activity.maximum_heart_rate_bpm,
        "maximum_speed_mps": activity.maximum_speed_mps,
        "min_altitude_meters": min_alt,
        "max_altitude_meters": max_alt,
        "estimated_elevation_gain_meters": gain,
        "lap_count": len(parsed.laps),
    }


def _lap_entry(lap: Lap) -> dict:
    """Build one ``lap_summary`` entry."""
    pace = _pace_seconds_per_km(
        lap.total_time_seconds, lap.distance_meters
    )
    return {
        "lap_index": lap.lap_index,
        "start_time": _iso(lap.start_time),
        "duration_minutes": _minutes(lap.total_time_seconds),
        "distance_km": _km(lap.distance_meters),
        "average_pace_seconds_per_km": _round1(pace),
        "average_pace_formatted": _format_pace(pace),
        "average_heart_rate_bpm": lap.average_heart_rate_bpm,
        "maximum_heart_rate_bpm": lap.maximum_heart_rate_bpm,
        "maximum_speed_mps": lap.maximum_speed_mps,
    }


def _trend_summary(parsed: ParsedActivity) -> dict:
    """Build the ``trend_summary`` section.

    Trackpoints are split into halves at the cumulative-distance
    midpoint. Pace uses timestamp and distance spans within each half;
    heart rate uses the average of valid readings within each half. A
    3% threshold separates ``faster_later`` / ``slower_later`` from
    ``stable``; missing data yields ``insufficient_data``.
    """
    notes: list[str] = []
    result = {
        "pace_trend": TREND_INSUFFICIENT,
        "heart_rate_trend": TREND_INSUFFICIENT,
        "first_half_average_pace_seconds_per_km": None,
        "second_half_average_pace_seconds_per_km": None,
        "first_half_average_heart_rate_bpm": None,
        "second_half_average_heart_rate_bpm": None,
        "method": _TREND_METHOD,
        "notes": notes,
    }

    midpoint = _distance_midpoint(parsed)
    if midpoint is None:
        notes.append(
            "Distance data is insufficient to split the activity "
            "into halves; trends are 'insufficient_data'."
        )
        return result

    first_half = [
        tp
        for tp in parsed.trackpoints
        if tp.distance_meters is not None
        and tp.distance_meters <= midpoint
    ]
    second_half = [
        tp
        for tp in parsed.trackpoints
        if tp.distance_meters is not None
        and tp.distance_meters > midpoint
    ]
    # Pace needs a time/distance span, so the midpoint boundary sample
    # is shared with the second half; otherwise a sparse second half
    # with only a finish sample would wrongly report insufficient_data.
    second_half_for_pace = [
        tp
        for tp in parsed.trackpoints
        if tp.distance_meters is not None
        and tp.distance_meters >= midpoint
    ]

    first_pace = _segment_pace(first_half)
    second_pace = _segment_pace(second_half_for_pace)
    result["first_half_average_pace_seconds_per_km"] = _round1(
        first_pace
    )
    result["second_half_average_pace_seconds_per_km"] = _round1(
        second_pace
    )
    if first_pace is not None and second_pace is not None:
        result["pace_trend"] = _pace_trend(first_pace, second_pace)
    else:
        notes.append(
            "Timestamp or distance data is insufficient to compute "
            "half-split pace; pace trend is 'insufficient_data'."
        )

    first_hr = _segment_heart_rate(first_half)
    second_hr = _segment_heart_rate(second_half)
    result["first_half_average_heart_rate_bpm"] = _round1(first_hr)
    result["second_half_average_heart_rate_bpm"] = _round1(second_hr)
    if first_hr is not None and second_hr is not None:
        result["heart_rate_trend"] = _heart_rate_trend(
            first_hr, second_hr
        )
    else:
        notes.append(
            "Heart rate data is insufficient in at least one half; "
            "heart rate trend is 'insufficient_data'."
        )

    return result


def _privacy_summary(parsed: ParsedActivity) -> dict:
    """Build the ``privacy`` section."""
    return {
        "gps_policy": parsed.privacy.gps_policy,
        "gps_included_in_summary": False,
        "route_details_included": False,
    }


def _data_quality(parsed: ParsedActivity) -> dict:
    """Build the ``data_quality`` section."""
    trackpoints = parsed.trackpoints
    notes: list[str] = []

    warning_codes: list[str] = []
    for warning in parsed.warnings:
        if warning.code not in warning_codes:
            warning_codes.append(warning.code)

    gps_count = sum(
        1
        for tp in trackpoints
        if tp.latitude is not None and tp.longitude is not None
    )
    hr_count = _coverage(trackpoints, "heart_rate_bpm")
    distance_count = _coverage(trackpoints, "distance_meters")
    speed_count = _coverage(trackpoints, "speed_mps")
    altitude_count = _coverage(trackpoints, "altitude_meters")
    timestamp_count = _coverage(trackpoints, "timestamp")

    missing = _missing_activity_fields(parsed)
    trackpoint_coverage = {
        "trackpoints.timestamp": timestamp_count,
        "trackpoints.distance_meters": distance_count,
        "trackpoints.heart_rate_bpm": hr_count,
        "trackpoints.altitude_meters": altitude_count,
        "trackpoints.speed_mps": speed_count,
    }
    for name, count in trackpoint_coverage.items():
        if count == 0:
            missing.append(name)

    if not trackpoints:
        notes.append("No trackpoints are available.")
    if altitude_count < 2:
        notes.append(
            "Fewer than two altitude readings; elevation gain "
            "cannot be estimated."
        )
    if missing:
        notes.append(
            "Some key fields are missing; see missing_key_fields."
        )

    return {
        "warnings_count": len(parsed.warnings),
        "warning_codes": warning_codes,
        "missing_key_fields": missing,
        "trackpoints_count": len(trackpoints),
        "trackpoints_with_gps_count": gps_count,
        "trackpoints_with_heart_rate_count": hr_count,
        "trackpoints_with_distance_count": distance_count,
        "trackpoints_with_speed_count": speed_count,
        "trackpoints_with_altitude_count": altitude_count,
        "notes": notes,
    }


def _ai_context(
    activity_summary: dict,
    key_metrics: dict,
    trend_summary: dict,
    privacy: dict,
) -> str:
    """Build the ``ai_context`` factual text block."""
    parts = [
        "This is a factual summary of a Running activity parsed "
        "from a Garmin TCX export; it is intended as input for "
        "further data analysis.",
        f"Duration: {_md(activity_summary['duration_minutes'])} "
        "minutes.",
        f"Distance: {_md(activity_summary['distance_km'])} km.",
        "Average pace: "
        f"{_md(key_metrics['average_pace_formatted'])}.",
        "Average heart rate: "
        f"{_md(key_metrics['average_heart_rate_bpm'])} bpm.",
        f"Laps: {activity_summary['lap_count']}.",
        f"Pace trend: {trend_summary['pace_trend']}.",
        f"Heart rate trend: {trend_summary['heart_rate_trend']}.",
        f"GPS policy: {privacy['gps_policy']}; GPS coordinates and "
        "route details are excluded from this summary.",
        "This summary contains no coaching advice and no medical "
        "interpretation.",
    ]
    return " ".join(parts)


# --- trend helpers -----------------------------------------------------


def _distance_midpoint(parsed: ParsedActivity) -> float | None:
    """Return half of the total activity distance, if determinable.

    Prefers ``activity.distance_meters``; falls back to the maximum
    trackpoint cumulative distance. Returns ``None`` when neither is
    available and positive.
    """
    total = parsed.activity.distance_meters
    if total is None or total <= 0:
        distances = [
            tp.distance_meters
            for tp in parsed.trackpoints
            if tp.distance_meters is not None
        ]
        total = max(distances) if distances else None
    if total is None or total <= 0:
        return None
    return total / 2.0


def _segment_pace(trackpoints: list[Trackpoint]) -> float | None:
    """Compute average pace (s/km) over a trackpoint segment.

    Uses the timestamp and cumulative-distance spans of the points
    that carry both fields. Returns ``None`` when fewer than two such
    points exist or the spans are not positive.
    """
    points = [
        tp
        for tp in trackpoints
        if tp.timestamp is not None and tp.distance_meters is not None
    ]
    if len(points) < 2:
        return None
    time_span = (
        points[-1].timestamp - points[0].timestamp
    ).total_seconds()
    distance_span = (
        points[-1].distance_meters - points[0].distance_meters
    )
    if time_span <= 0 or distance_span <= 0:
        return None
    return time_span / (distance_span / 1000.0)


def _segment_heart_rate(
    trackpoints: list[Trackpoint],
) -> float | None:
    """Average valid heart rate over a segment, or ``None`` if empty."""
    values = [
        tp.heart_rate_bpm
        for tp in trackpoints
        if tp.heart_rate_bpm is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _pace_trend(first: float, second: float) -> str:
    """Label the pace trend; lower pace seconds mean faster."""
    if second < first * (1.0 - TREND_THRESHOLD):
        return TREND_FASTER_LATER
    if second > first * (1.0 + TREND_THRESHOLD):
        return TREND_SLOWER_LATER
    return TREND_STABLE


def _heart_rate_trend(first: float, second: float) -> str:
    """Label the heart rate trend; higher later HR maps to slower."""
    if second > first * (1.0 + TREND_THRESHOLD):
        return TREND_SLOWER_LATER
    if second < first * (1.0 - TREND_THRESHOLD):
        return TREND_FASTER_LATER
    return TREND_STABLE


# --- metric helpers ----------------------------------------------------


def _altitude_stats(
    trackpoints: list[Trackpoint],
) -> tuple[float | None, float | None, float | None]:
    """Return (min altitude, max altitude, estimated gain).

    Gain sums only positive deltas between consecutive valid altitude
    readings and is ``None`` when fewer than two readings exist.
    """
    altitudes = [
        tp.altitude_meters
        for tp in trackpoints
        if tp.altitude_meters is not None
    ]
    if not altitudes:
        return None, None, None
    min_alt = min(altitudes)
    max_alt = max(altitudes)
    if len(altitudes) < 2:
        return min_alt, max_alt, None
    gain = sum(
        later - earlier
        for earlier, later in zip(altitudes, altitudes[1:])
        if later > earlier
    )
    return min_alt, max_alt, round(gain, 1)


def _pace_seconds_per_km(
    total_time_seconds: float | None,
    distance_meters: float | None,
) -> float | None:
    """Average pace in seconds per km, or ``None`` if not computable."""
    if total_time_seconds is None or total_time_seconds <= 0:
        return None
    if distance_meters is None or distance_meters <= 0:
        return None
    return total_time_seconds / (distance_meters / 1000.0)


def _format_pace(pace_seconds_per_km: float | None) -> str | None:
    """Format pace seconds as ``mm:ss/km`` (rounded to whole seconds)."""
    if pace_seconds_per_km is None:
        return None
    total = int(round(pace_seconds_per_km))
    minutes, seconds = divmod(total, 60)
    return f"{minutes:02d}:{seconds:02d}/km"


def _minutes(total_time_seconds: float | None) -> float | None:
    """Convert seconds to minutes rounded to 2 decimals."""
    if total_time_seconds is None:
        return None
    return round(total_time_seconds / 60.0, 2)


def _km(distance_meters: float | None) -> float | None:
    """Convert meters to kilometers rounded to 3 decimals."""
    if distance_meters is None:
        return None
    return round(distance_meters / 1000.0, 3)


def _round1(value: float | None) -> float | None:
    """Round to 1 decimal, passing ``None`` through."""
    if value is None:
        return None
    return round(value, 1)


def _iso(value: datetime | None) -> str | None:
    """Serialize a datetime to an ISO 8601 UTC string (``Z`` suffix)."""
    if value is None:
        return None
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _coverage(trackpoints: list[Trackpoint], field: str) -> int:
    """Count trackpoints whose *field* attribute is not ``None``."""
    return sum(
        1 for tp in trackpoints if getattr(tp, field) is not None
    )


def _missing_activity_fields(parsed: ParsedActivity) -> list[str]:
    """List activity-level key fields that are missing."""
    activity = parsed.activity
    checks = {
        "activity.start_time": activity.start_time,
        "activity.total_time_seconds": activity.total_time_seconds,
        "activity.distance_meters": activity.distance_meters,
        "activity.average_heart_rate_bpm": (
            activity.average_heart_rate_bpm
        ),
        "activity.maximum_heart_rate_bpm": (
            activity.maximum_heart_rate_bpm
        ),
    }
    return [name for name, value in checks.items() if value is None]


# --- markdown helpers --------------------------------------------------


def _md(value: object) -> str:
    """Render a value for Markdown; ``None`` becomes ``unavailable``."""
    if value is None:
        return "unavailable"
    return str(value)


def _md_unit(value: object, unit: str) -> str:
    """Render a value with a unit suffix, or ``unavailable``."""
    if value is None:
        return "unavailable"
    return f"{value} {unit}"


def _md_pace(value: float | None) -> str:
    """Render half-split pace seconds with its formatted twin."""
    if value is None:
        return "unavailable"
    return f"{value} s/km ({_format_pace(value)})"


def _lap_table(lap_summary: list[dict]) -> list[str]:
    """Render the lap summary as Markdown table lines."""
    if not lap_summary:
        return ["No lap data is available."]
    header = (
        "| Lap | Start time | Duration (min) | Distance (km) "
        "| Pace | Avg HR | Max HR | Max speed (m/s) |"
    )
    divider = "|---|---|---|---|---|---|---|---|"
    rows = [header, divider]
    for lap in lap_summary:
        rows.append(
            f"| {_md(lap['lap_index'])} "
            f"| {_md(lap['start_time'])} "
            f"| {_md(lap['duration_minutes'])} "
            f"| {_md(lap['distance_km'])} "
            f"| {_md(lap['average_pace_formatted'])} "
            f"| {_md(lap['average_heart_rate_bpm'])} "
            f"| {_md(lap['maximum_heart_rate_bpm'])} "
            f"| {_md(lap['maximum_speed_mps'])} |"
        )
    return rows
