"""Normalize parsed TCX activities and apply GPS privacy policy.

The normalizer converts raw parser output into a data-contract-compliant
:class:`ParsedActivity`. It keeps missing values as ``None``, records the
requested GPS policy, ensures source metadata does not leak absolute local
paths, and derives pace from speed where possible. Serialization to strings
(ISO 8601 timestamps, etc.) is deferred to the exporters.
"""

from __future__ import annotations

import copy
from pathlib import Path

from garmin_tcx_ai.models import GpsPolicy, ParsedActivity
from garmin_tcx_ai.privacy import apply_gps_policy


def normalize_activity(
    parsed: ParsedActivity,
    gps_policy: GpsPolicy = "keep",
) -> ParsedActivity:
    """Normalize parsed TCX activity data and apply GPS privacy policy.

    Returns a new :class:`ParsedActivity`; the input is never mutated. The
    result keeps missing values as ``None``, records *gps_policy*, strips any
    directory component from source and warning file references, derives
    ``pace_seconds_per_km`` from ``speed_mps`` when available, and preserves
    ``datetime`` objects for the exporters to serialize.
    """
    result = copy.deepcopy(parsed)

    _sanitize_source(result)
    _sanitize_warnings(result)
    _derive_pace(result)

    # Delegate GPS handling (and privacy metadata) to the privacy module.
    # It returns another copy, which is safe since *result* is already local.
    return apply_gps_policy(result, gps_policy)


def _sanitize_source(activity: ParsedActivity) -> None:
    """Ensure ``source.file_name`` contains only a bare file name."""
    file_name = activity.source.file_name
    if file_name:
        activity.source.file_name = Path(file_name).name


def _sanitize_warnings(activity: ParsedActivity) -> None:
    """Strip any directory component from warning ``source_file`` fields."""
    for warning in activity.warnings:
        if warning.source_file:
            warning.source_file = Path(warning.source_file).name


def _derive_pace(activity: ParsedActivity) -> None:
    """Compute ``pace_seconds_per_km`` from ``speed_mps`` when positive."""
    for tp in activity.trackpoints:
        speed = tp.speed_mps
        if speed is not None and speed > 0:
            tp.pace_seconds_per_km = round(1000.0 / speed, 2)
