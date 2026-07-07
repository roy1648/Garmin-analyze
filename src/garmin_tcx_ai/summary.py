"""AI-ready factual summary builder for normalized activities.

This module turns a normalized :class:`ParsedActivity` into the
``ai_summary.json`` payload defined in ``docs/02_data_contract.md`` and
renders the matching ``ai_summary.md`` text. The summary is strictly
factual: it never includes GPS coordinates or route details and it does
not produce coaching or medical interpretation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from garmin_tcx_ai.models import Lap, ParsedActivity, Trackpoint

_SPLIT_METHOD = "split_at_cumulative_distance_midpoint"
_SPLIT_POLICY = "computed_metrics_only_no_training_interpretation"
_SPLIT_INTERPRETATION_LEVEL = (
    "limited_for_interval_or_mixed_lap_activity"
)
_SPLIT_DISCLAIMER = (
    "This split metric is a fixed-formula summary and must not be "
    "interpreted as fatigue, workout quality, or workout type."
)
_ELEVATION_GAIN_METHOD = "sum_positive_consecutive_altitude_deltas"


def build_ai_summary(
    activity: ParsedActivity,
    timezone_name: str = "Asia/Taipei",
) -> dict:
    """Build an AI-ready factual summary for a normalized Running
    activity.

    Returns a JSON-serializable dict with the top-level keys
    ``activity_summary``, ``key_metrics``, ``lap_summary``,
    ``computed_split_metrics``, ``privacy``, ``data_quality`` and
    ``data_policy``.
    Missing values are ``None`` and datetimes are ISO 8601 strings. GPS
    coordinates and route details are never included.
    """
    zone = _timezone(timezone_name)
    activity_summary = _activity_summary(activity, zone, timezone_name)
    key_metrics = _key_metrics(activity)
    lap_summary = [
        _lap_entry(lap, activity.trackpoints) for lap in activity.laps
    ]
    split_metrics = _computed_split_metrics(activity)
    privacy = _privacy_summary(activity)
    data_quality = _data_quality(activity)
    return {
        "activity_summary": activity_summary,
        "key_metrics": key_metrics,
        "lap_summary": lap_summary,
        "computed_split_metrics": split_metrics,
        "privacy": privacy,
        "data_quality": data_quality,
        "data_policy": _data_policy(),
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
    split = summary["computed_split_metrics"]
    privacy = summary["privacy"]
    quality = summary["data_quality"]

    lines: list[str] = ["# Running Activity Summary", ""]

    lines += ["## Activity", ""]
    lines += [
        f"- Sport: {_md(act['sport'])}",
        f"- Activity ID: {_md(act['activity_id'])}",
        f"- Start time: {_md(act['start_time'])}",
        f"- Local start time: {_md(act['start_time_local'])}",
        f"- Local date: {_md(act['local_date'])}",
        f"- Timezone: {_md(act['timezone'])}",
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
        "- Average run cadence raw: "
        f"{_md(metrics['cadence']['avg_run_cadence_raw'])}",
        f"- Average watts: {_md(metrics['power']['avg_watts'])}",
        "",
    ]

    lines += ["## Lap Summary", ""]
    lines += _lap_table(summary["lap_summary"])
    lines.append("")

    lines += ["## Computed Split Metrics", ""]
    lines += [
        "- First half average pace: "
        f"{_md_pace(split['first_half_average_pace_seconds_per_km'])}",
        "- Second half average pace: "
        f"{_md_pace(split['second_half_average_pace_seconds_per_km'])}",
        "- Pace second-half delta: "
        f"{_md_unit(split['pace_second_half_delta_seconds_per_km'], 's/km')}",
        "- First half average heart rate: "
        f"{_md_unit(split['first_half_average_heart_rate_bpm'], 'bpm')}",
        "- Second half average heart rate: "
        f"{_md_unit(split['second_half_average_heart_rate_bpm'], 'bpm')}",
        "- Heart-rate second-half delta: "
        f"{_md_unit(split['heart_rate_second_half_delta_bpm'], 'bpm')}",
        f"- Method: {split['method']}",
        f"- Interpretation policy: {split['interpretation_policy']}",
        f"- Interpretation level: {split['interpretation_level']}",
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
        "- Elevation gain method: "
        f"{metrics['estimated_elevation_gain_method']}",
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

    lines += ["## Data Policy", ""]
    policy = summary["data_policy"]
    lines += [
        f"- Source: {policy['source']}",
        "- Workout role inference: disabled.",
        "- Coaching advice: disabled.",
        "- Medical interpretation: disabled.",
        "",
    ]

    return "\n".join(lines)


# --- section builders -------------------------------------------------


def _activity_summary(
    parsed: ParsedActivity,
    zone: tzinfo,
    timezone_name: str,
) -> dict:
    """Build the ``activity_summary`` section."""
    activity = parsed.activity
    local_start = _local_time(activity.start_time, zone)
    return {
        "sport": activity.sport,
        "activity_id": activity.activity_id,
        "start_time": _iso(activity.start_time),
        "start_time_local": _iso_offset(local_start),
        "timezone": timezone_name,
        "local_date": (
            local_start.date().isoformat() if local_start else None
        ),
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
        "estimated_elevation_gain_method": _ELEVATION_GAIN_METHOD,
        "lap_count": len(parsed.laps),
        "cadence": _cadence_metrics(
            parsed.trackpoints,
            "tcx_extension_RunCadence_or_normalized_trackpoint",
        ),
        "power": _power_metrics(
            parsed.trackpoints,
            "tcx_extension_Watts_or_normalized_trackpoint",
        ),
    }


def _lap_entry(lap: Lap, trackpoints: list[Trackpoint]) -> dict:
    """Build one ``lap_summary`` entry."""
    pace = _pace_seconds_per_km(
        lap.total_time_seconds, lap.distance_meters
    )
    lap_trackpoints = [
        point for point in trackpoints if point.lap_index == lap.lap_index
    ]
    reliability, reason = _pace_reliability(
        lap.distance_meters,
        lap.total_time_seconds,
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
        "pace_reliability": reliability,
        "reliability_reason": reason,
        "cadence": _cadence_metrics(
            lap_trackpoints,
            "normalized_trackpoints_by_lap",
        ),
        "power": _power_metrics(
            lap_trackpoints,
            "normalized_trackpoints_by_lap",
        ),
        "role": None,
        "role_source": "not_inferred",
    }


def _computed_split_metrics(parsed: ParsedActivity) -> dict:
    """Build neutral first/second-half metrics using fixed formulas."""
    notes = [_SPLIT_DISCLAIMER]
    result = {
        "method": _SPLIT_METHOD,
        "interpretation_policy": _SPLIT_POLICY,
        "interpretation_level": _SPLIT_INTERPRETATION_LEVEL,
        "first_half_average_pace_seconds_per_km": None,
        "second_half_average_pace_seconds_per_km": None,
        "pace_second_half_delta_seconds_per_km": None,
        "first_half_average_heart_rate_bpm": None,
        "second_half_average_heart_rate_bpm": None,
        "heart_rate_second_half_delta_bpm": None,
        "pace_data_available": False,
        "heart_rate_data_available": False,
        "data_available": False,
        "notes": notes,
    }

    midpoint = _distance_midpoint(parsed)
    if midpoint is None:
        notes.append(
            "Distance data is missing or insufficient for the fixed "
            "cumulative-distance midpoint split."
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
    second_half_for_pace = _second_half_pace_points(
        parsed.trackpoints, midpoint
    )

    first_pace = _segment_pace(first_half)
    second_pace = _segment_pace(second_half_for_pace)
    result["first_half_average_pace_seconds_per_km"] = _round1(
        first_pace
    )
    result["second_half_average_pace_seconds_per_km"] = _round1(
        second_pace
    )
    if first_pace is not None and second_pace is not None:
        result["pace_second_half_delta_seconds_per_km"] = _round1(
            second_pace - first_pace
        )
        result["pace_data_available"] = True
    else:
        notes.append(
            "Timestamp or distance data is missing or insufficient "
            "for half-split pace."
        )

    first_hr = _segment_heart_rate(first_half)
    second_hr = _segment_heart_rate(second_half)
    result["first_half_average_heart_rate_bpm"] = _round1(first_hr)
    result["second_half_average_heart_rate_bpm"] = _round1(second_hr)
    if first_hr is not None and second_hr is not None:
        result["heart_rate_second_half_delta_bpm"] = _round1(
            second_hr - first_hr
        )
        result["heart_rate_data_available"] = True
    else:
        notes.append(
            "Heart rate data is missing or insufficient in at least "
            "one half."
        )

    result["data_available"] = (
        result["pace_data_available"]
        and result["heart_rate_data_available"]
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
    cadence_count = _coverage(trackpoints, "run_cadence_spm")
    power_count = _coverage(trackpoints, "power_watts")

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
        "trackpoints_with_run_cadence_count": cadence_count,
        "trackpoints_with_power_count": power_count,
        "notes": notes,
    }


def _data_policy() -> dict:
    """Return the source and no-inference policy for summary data."""
    return {
        "source": "tcx_file",
        "allowed_content": [
            "raw_tcx_fields",
            "fixed_formula_metrics",
            "data_quality_flags",
            "privacy_policy",
        ],
        "no_workout_role_inference": True,
        "no_coaching_advice": True,
        "no_medical_interpretation": True,
        "manual_context_fields_are_placeholders": True,
    }


# --- split helpers -----------------------------------------------------


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


def _second_half_pace_points(
    trackpoints: list[Trackpoint], midpoint: float
) -> list[Trackpoint]:
    """Return trackpoints that bracket the midpoint for pace timing.

    Pace needs a time/distance span that actually crosses the
    midpoint. If no sample lands exactly on the midpoint, the strict
    "distance > midpoint" points alone may all sit close to the
    finish (or be a single point), understating or losing the span
    entirely. Anchoring with the last sample at or before the midpoint
    approximates the midpoint crossing without discarding real data.
    """
    with_distance = [
        tp for tp in trackpoints if tp.distance_meters is not None
    ]
    before = [tp for tp in with_distance if tp.distance_meters <= midpoint]
    after = [tp for tp in with_distance if tp.distance_meters > midpoint]
    if before and after:
        return [before[-1], *after]
    return after


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


# --- metric helpers ----------------------------------------------------


def _pace_reliability(
    distance_meters: float | None,
    duration_seconds: float | None,
) -> tuple[str, str]:
    """Classify lap pace reliability using fixed data-quality rules."""
    if distance_meters is None or duration_seconds is None:
        return "invalid", "missing_distance_or_duration"
    if distance_meters <= 0 or duration_seconds <= 0:
        return "invalid", "non_positive_distance_or_duration"
    if distance_meters < 100:
        return "low", "lap_distance_below_0.1km"
    if distance_meters < 300:
        return "medium", "lap_distance_between_0.1km_and_0.3km"
    return "high", "lap_distance_at_least_0.3km"


def _cadence_metrics(
    trackpoints: list[Trackpoint],
    source: str,
) -> dict:
    """Aggregate raw Garmin run-cadence values without conversion."""
    values = [
        point.run_cadence_spm
        for point in trackpoints
        if point.run_cadence_spm is not None
    ]
    return {
        "avg_run_cadence_raw": _average(values),
        "max_run_cadence_raw": max(values) if values else None,
        "trackpoints_with_run_cadence_count": len(values),
        "source": source,
        "avg_cadence_spm": None,
        "conversion_rule": None,
    }


def _power_metrics(
    trackpoints: list[Trackpoint],
    source: str,
) -> dict:
    """Aggregate raw TCX power values without interpretation."""
    values = [
        point.power_watts
        for point in trackpoints
        if point.power_watts is not None
    ]
    return {
        "avg_watts": _average(values),
        "max_watts": max(values) if values else None,
        "trackpoints_with_power_count": len(values),
        "source": source,
    }


def _average(values: list[int]) -> float | None:
    """Return a one-decimal arithmetic mean for integer samples."""
    if not values:
        return None
    return round(sum(values) / len(values), 1)


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


def _local_time(value: datetime | None, zone: tzinfo) -> datetime | None:
    """Convert a recorded timestamp to the configured timezone."""
    if value is None:
        return None
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(zone)


def _iso_offset(value: datetime | None) -> str | None:
    """Serialize a datetime while preserving its UTC offset."""
    if value is None:
        return None
    return value.isoformat()


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
        "| Pace | Pace reliability | Reliability reason | Avg HR "
        "| Max HR | Max speed (m/s) | Avg cadence raw | Avg watts |"
    )
    divider = "|---|---|---|---|---|---|---|---|---|---|---|---|"
    rows = [header, divider]
    for lap in lap_summary:
        rows.append(
            f"| {_md(lap['lap_index'])} "
            f"| {_md(lap['start_time'])} "
            f"| {_md(lap['duration_minutes'])} "
            f"| {_md(lap['distance_km'])} "
            f"| {_md(lap['average_pace_formatted'])} "
            f"| {_md(lap['pace_reliability'])} "
            f"| {_md(lap['reliability_reason'])} "
            f"| {_md(lap['average_heart_rate_bpm'])} "
            f"| {_md(lap['maximum_heart_rate_bpm'])} "
            f"| {_md(lap['maximum_speed_mps'])} "
            f"| {_md(lap['cadence']['avg_run_cadence_raw'])} "
            f"| {_md(lap['power']['avg_watts'])} |"
        )
    return rows
