"""Garmin TCX AI package scaffold."""

from garmin_tcx_ai.exporters import (
    safe_activity_id,
    write_activity_json,
    write_trackpoints_csv,
)
from garmin_tcx_ai.normalizer import normalize_activity
from garmin_tcx_ai.privacy import apply_gps_policy

__all__ = [
    "__version__",
    "apply_gps_policy",
    "normalize_activity",
    "safe_activity_id",
    "write_activity_json",
    "write_trackpoints_csv",
]

__version__ = "0.1.0"
