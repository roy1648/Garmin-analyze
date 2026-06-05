"""Internal data models for normalized Garmin TCX activities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

WarningSeverity = Literal["info", "warning", "error"]
GpsPolicy = Literal["keep", "remove", "redact_start_end"]


@dataclass
class WarningRecord:
    """Describe a warning produced while processing a source file."""

    code: str
    severity: WarningSeverity
    field: str | None
    message: str
    source_file: str


@dataclass
class SourceInfo:
    """Describe the source file used to create an activity."""

    format: str
    file_name: str
    file_path: str


@dataclass
class PrivacyInfo:
    """Describe the privacy policy applied to activity data."""

    gps_policy: GpsPolicy = "keep"


@dataclass
class Activity:
    """Represent normalized activity-level data."""

    sport: str | None = None
    activity_id: str | None = None
    start_time: datetime | None = None
    total_time_seconds: float | None = None
    distance_meters: float | None = None
    calories: int | None = None
    average_heart_rate_bpm: int | None = None
    maximum_heart_rate_bpm: int | None = None
    maximum_speed_mps: float | None = None


@dataclass
class Lap:
    """Represent normalized lap-level data."""

    lap_index: int | None = None
    start_time: datetime | None = None
    total_time_seconds: float | None = None
    distance_meters: float | None = None
    calories: int | None = None
    average_heart_rate_bpm: int | None = None
    maximum_heart_rate_bpm: int | None = None
    maximum_speed_mps: float | None = None
    intensity: str | None = None
    trigger_method: str | None = None


@dataclass
class Trackpoint:
    """Represent normalized trackpoint-level data."""

    trackpoint_index: int | None = None
    lap_index: int | None = None
    timestamp: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_meters: float | None = None
    distance_meters: float | None = None
    heart_rate_bpm: int | None = None
    speed_mps: float | None = None
    pace_seconds_per_km: float | None = None
    run_cadence_spm: int | None = None
    power_watts: int | None = None


@dataclass
class ParsedActivity:
    """Combine normalized activity data and processing metadata."""

    source: SourceInfo
    privacy: PrivacyInfo
    activity: Activity
    laps: list[Lap] = field(default_factory=list)
    trackpoints: list[Trackpoint] = field(default_factory=list)
    warnings: list[WarningRecord] = field(default_factory=list)
