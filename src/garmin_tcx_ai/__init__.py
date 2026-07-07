"""Garmin TCX AI package scaffold."""

from garmin_tcx_ai.exporters import (
    safe_activity_id,
    write_activity_json,
    write_ai_summary_json,
    write_ai_summary_markdown,
    write_session_bundle_json,
    write_session_bundle_markdown,
    write_trackpoints_csv,
)
from garmin_tcx_ai.normalizer import normalize_activity
from garmin_tcx_ai.privacy import apply_gps_policy
from garmin_tcx_ai.summary import (
    build_ai_summary,
    render_ai_summary_markdown,
)
from garmin_tcx_ai.session import (
    build_session_bundle,
    render_session_bundle_markdown,
)

__all__ = [
    "__version__",
    "apply_gps_policy",
    "build_ai_summary",
    "build_session_bundle",
    "normalize_activity",
    "render_ai_summary_markdown",
    "render_session_bundle_markdown",
    "safe_activity_id",
    "write_activity_json",
    "write_ai_summary_json",
    "write_ai_summary_markdown",
    "write_session_bundle_json",
    "write_session_bundle_markdown",
    "write_trackpoints_csv",
]

__version__ = "0.1.0"
