"""Parser for Garmin Connect Running TCX files."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError

from garmin_tcx_ai.models import (
    Activity,
    Lap,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
    WarningRecord,
)

TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
AEX_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"
NS = {"tcx": TCX_NS, "ns3": AEX_NS}

SUPPORTED_SPORTS = {"Running"}


class TCXParseError(Exception):
    """Raised when a TCX file cannot be parsed."""


class UnsupportedActivityError(Exception):
    """Raised when a TCX activity type is not supported by the MVP."""


def _tag(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def _text(el: ElementTree.Element | None) -> str | None:
    if el is None:
        return None
    return el.text


def _float(el: ElementTree.Element | None) -> float | None:
    t = _text(el)
    if t is None:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _int(el: ElementTree.Element | None) -> int | None:
    v = _float(el)
    return None if v is None else int(round(v))


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _find_text(
    parent: ElementTree.Element, path: str
) -> str | None:
    el = parent.find(path, NS)
    return _text(el)


def _parse_lap(
    lap_el: ElementTree.Element, lap_index: int
) -> Lap:
    start_time = _parse_time(lap_el.get("StartTime"))

    total_time = _float(lap_el.find("tcx:TotalTimeSeconds", NS))
    distance = _float(lap_el.find("tcx:DistanceMeters", NS))
    calories = _int(lap_el.find("tcx:Calories", NS))
    intensity = _find_text(lap_el, "tcx:Intensity")
    trigger = _find_text(lap_el, "tcx:TriggerMethod")
    max_speed = _float(lap_el.find("tcx:MaximumSpeed", NS))

    avg_hr_el = lap_el.find("tcx:AverageHeartRateBpm/tcx:Value", NS)
    avg_hr = _int(avg_hr_el)

    max_hr_el = lap_el.find("tcx:MaximumHeartRateBpm/tcx:Value", NS)
    max_hr = _int(max_hr_el)

    return Lap(
        lap_index=lap_index,
        start_time=start_time,
        total_time_seconds=total_time,
        distance_meters=distance,
        calories=calories,
        average_heart_rate_bpm=avg_hr,
        maximum_heart_rate_bpm=max_hr,
        maximum_speed_mps=max_speed,
        intensity=intensity,
        trigger_method=trigger,
    )


def _parse_trackpoint(
    tp_el: ElementTree.Element,
    trackpoint_index: int,
    lap_index: int,
) -> Trackpoint:
    timestamp = _parse_time(_find_text(tp_el, "tcx:Time"))
    lat = _float(tp_el.find("tcx:Position/tcx:LatitudeDegrees", NS))
    lon = _float(tp_el.find("tcx:Position/tcx:LongitudeDegrees", NS))
    alt = _float(tp_el.find("tcx:AltitudeMeters", NS))
    dist = _float(tp_el.find("tcx:DistanceMeters", NS))

    hr_el = tp_el.find("tcx:HeartRateBpm/tcx:Value", NS)
    hr = _int(hr_el)

    # Garmin extensions: Speed, RunCadence, Watts
    tpx = tp_el.find("tcx:Extensions/ns3:TPX", NS)
    speed: float | None = None
    cadence: int | None = None
    power: int | None = None

    if tpx is not None:
        speed = _float(tpx.find("ns3:Speed", NS))
        cadence = _int(tpx.find("ns3:RunCadence", NS))
        power = _int(tpx.find("ns3:Watts", NS))

    # Fall back to standard TCX Cadence element if not found in extensions
    if cadence is None:
        cadence = _int(tp_el.find("tcx:Cadence", NS))

    pace: float | None = None
    if speed is not None and speed > 0:
        pace = round(1000.0 / speed, 2)

    return Trackpoint(
        trackpoint_index=trackpoint_index,
        lap_index=lap_index,
        timestamp=timestamp,
        latitude=lat,
        longitude=lon,
        altitude_meters=alt,
        distance_meters=dist,
        heart_rate_bpm=hr,
        speed_mps=speed,
        pace_seconds_per_km=pace,
        run_cadence_spm=cadence,
        power_watts=power,
    )


def parse_tcx(file_path: str | Path) -> ParsedActivity:
    """Parse a Garmin TCX file and return a ParsedActivity.

    Supports Running activities only for MVP.

    Raises:
        FileNotFoundError: if *file_path* does not exist.
        TCXParseError: if the file contains invalid XML.
        UnsupportedActivityError: if the activity sport is not Running.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"TCX file not found: {path}"
        )

    file_name = path.name
    file_path_str = str(path)

    try:
        tree = ElementTree.parse(path)
    except ParseError as exc:
        raise TCXParseError(
            f"Invalid XML in '{file_name}': {exc}"
        ) from exc

    root = tree.getroot()

    # Handle both namespaced and un-namespaced roots gracefully
    activity_el = root.find(".//tcx:Activity", NS)
    if activity_el is None:
        raise TCXParseError(
            f"No <Activity> element found in '{file_name}'."
        )

    sport = activity_el.get("Sport")
    if sport not in SUPPORTED_SPORTS:
        raise UnsupportedActivityError(
            f"Activity sport '{sport}' is not supported for MVP. "
            f"Only Running is supported."
        )

    activity_id = _find_text(activity_el, "tcx:Id")
    start_time = _parse_time(activity_id)

    # Look for activity-level aggregates directly under Activity,
    # NOT in Lap descendants. Use findall to check for direct children.
    act_total_time = None
    act_distance = None
    act_calories = None

    for child in activity_el:
        if child.tag == _tag(TCX_NS, "TotalTimeSeconds"):
            act_total_time = _float(child)
        elif child.tag == _tag(TCX_NS, "DistanceMeters"):
            act_distance = _float(child)
        elif child.tag == _tag(TCX_NS, "Calories"):
            act_calories = _int(child)

    # For activity-level HR aggregates, do NOT search descendants.
    # These are rare and often only present at lap level.
    # Keep them as None for MVP; future hardening can derive them.
    act_avg_hr = None
    act_max_hr = None

    # Similarly, MaximumSpeed at activity level may not exist;
    # it will be derived from laps below if not present.
    act_max_speed = None
    for child in activity_el:
        if child.tag == _tag(TCX_NS, "MaximumSpeed"):
            act_max_speed = _float(child)
            break

    lap_elements = activity_el.findall("tcx:Lap", NS)
    laps: list[Lap] = []
    trackpoints: list[Trackpoint] = []
    warnings: list[WarningRecord] = []
    tp_global_index = 1

    for lap_idx, lap_el in enumerate(lap_elements, start=1):
        lap = _parse_lap(lap_el, lap_idx)
        laps.append(lap)

        track_els = lap_el.findall("tcx:Track", NS)
        for track_el in track_els:
            for tp_el in track_el.findall("tcx:Trackpoint", NS):
                tp = _parse_trackpoint(tp_el, tp_global_index, lap_idx)
                trackpoints.append(tp)
                tp_global_index += 1

    # Fall back to lap-level data for activity summary if not found higher
    if act_total_time is None and laps:
        valid = [
            lap.total_time_seconds
            for lap in laps
            if lap.total_time_seconds is not None
        ]
        if valid:
            act_total_time = sum(valid)

    if act_distance is None and laps:
        valid_d = [
            lap.distance_meters
            for lap in laps
            if lap.distance_meters is not None
        ]
        if valid_d:
            act_distance = sum(valid_d)

    if act_calories is None and laps:
        valid_c = [
            lap.calories
            for lap in laps
            if lap.calories is not None
        ]
        if valid_c:
            act_calories = sum(valid_c)

    if act_max_speed is None and laps:
        valid_s = [
            lap.maximum_speed_mps
            for lap in laps
            if lap.maximum_speed_mps is not None
        ]
        if valid_s:
            act_max_speed = max(valid_s)

    # Derive activity-level HR aggregates from laps if not found at
    # activity level
    if act_avg_hr is None and laps:
        valid_avg_hr = [
            lap.average_heart_rate_bpm
            for lap in laps
            if lap.average_heart_rate_bpm is not None
        ]
        if valid_avg_hr:
            act_avg_hr = int(sum(valid_avg_hr) / len(valid_avg_hr))

    if act_max_hr is None and laps:
        valid_max_hr = [
            lap.maximum_heart_rate_bpm
            for lap in laps
            if lap.maximum_heart_rate_bpm is not None
        ]
        if valid_max_hr:
            act_max_hr = max(valid_max_hr)

    # Emit warnings for completely missing optional fields
    if not trackpoints:
        warnings.append(
            WarningRecord(
                code="missing_optional_field",
                severity="warning",
                field="trackpoints",
                message="No trackpoints found in the source file.",
                source_file=file_name,
            )
        )

    activity = Activity(
        sport=sport,
        activity_id=activity_id,
        start_time=start_time,
        total_time_seconds=act_total_time,
        distance_meters=act_distance,
        calories=act_calories,
        average_heart_rate_bpm=act_avg_hr,
        maximum_heart_rate_bpm=act_max_hr,
        maximum_speed_mps=act_max_speed,
    )

    source = SourceInfo(
        format="tcx",
        file_name=file_name,
        file_path=file_path_str,
    )
    privacy = PrivacyInfo(gps_policy="keep")

    return ParsedActivity(
        source=source,
        privacy=privacy,
        activity=activity,
        laps=laps,
        trackpoints=trackpoints,
        warnings=warnings,
    )
