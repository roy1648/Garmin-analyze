"""GPS privacy policy handling for parsed TCX activities.

This module applies the GPS privacy policies defined in
``docs/02_data_contract.md`` to a :class:`ParsedActivity`. Policies operate
on trackpoint latitude/longitude values only and never touch the raw source
file.
"""

from __future__ import annotations

import copy
import math

from garmin_tcx_ai.models import GpsPolicy, ParsedActivity, Trackpoint

# Distance-based redaction window (meters) for ``redact_start_end``.
REDACT_DISTANCE_METERS = 300.0

# Fraction of trackpoints redacted at each end when distance data is
# insufficient for ``redact_start_end``.
REDACT_FALLBACK_FRACTION = 0.10


def apply_gps_policy(
    activity: ParsedActivity,
    policy: GpsPolicy = "keep",
) -> ParsedActivity:
    """Return a copy of *activity* with the GPS privacy *policy* applied.

    The input object is never mutated. The returned copy has
    ``privacy.gps_policy`` set to *policy* and trackpoint coordinates
    adjusted according to the policy:

    * ``keep`` preserves all latitude/longitude values.
    * ``remove`` sets every latitude/longitude to ``None``.
    * ``redact_start_end`` removes coordinates near the start and end of the
      activity (see :func:`_redact_start_end`).
    """
    result = copy.deepcopy(activity)
    result.privacy.gps_policy = policy

    if policy == "keep":
        return result
    if policy == "remove":
        _remove_all(result.trackpoints)
        return result
    if policy == "redact_start_end":
        _redact_start_end(result.trackpoints)
        return result

    raise ValueError(f"Unsupported gps_policy: {policy!r}")


def _remove_all(trackpoints: list[Trackpoint]) -> None:
    """Set latitude and longitude to ``None`` for every trackpoint."""
    for tp in trackpoints:
        tp.latitude = None
        tp.longitude = None


def _clear_coords(tp: Trackpoint) -> None:
    """Redact a single trackpoint's coordinates in place."""
    tp.latitude = None
    tp.longitude = None


def _redact_start_end(trackpoints: list[Trackpoint]) -> None:
    """Redact coordinates near the start and end of the activity.

    Primary strategy uses cumulative ``distance_meters`` to redact the first
    and last :data:`REDACT_DISTANCE_METERS` meters. When distance data is
    insufficient, it falls back to redacting the first and last
    :data:`REDACT_FALLBACK_FRACTION` of trackpoints. When the activity is too
    short to preserve a middle segment, all coordinates are redacted.
    """
    if not trackpoints:
        return

    distances = [
        tp.distance_meters
        for tp in trackpoints
        if tp.distance_meters is not None
    ]
    total = max(distances) if distances else None

    # Distance data is usable only when most points carry a cumulative
    # distance and the activity actually covers ground.
    distance_usable = (
        len(distances) >= 2
        and total is not None
        and total > 0
    )

    if not distance_usable:
        _redact_by_fraction(trackpoints)
        return

    # Too short to keep any middle segment: redact everything.
    if total <= 2 * REDACT_DISTANCE_METERS:
        _remove_all(trackpoints)
        return

    tail_threshold = total - REDACT_DISTANCE_METERS
    for tp in trackpoints:
        dist = tp.distance_meters
        if dist is None:
            # Without a distance we cannot place the point safely; redact it.
            _clear_coords(tp)
            continue
        if dist <= REDACT_DISTANCE_METERS or dist >= tail_threshold:
            _clear_coords(tp)


def _redact_by_fraction(trackpoints: list[Trackpoint]) -> None:
    """Redact the first and last fraction of trackpoints by count."""
    n = len(trackpoints)
    edge = max(1, math.floor(n * REDACT_FALLBACK_FRACTION))

    # Not enough points to keep a middle segment: redact everything.
    if edge * 2 >= n:
        _remove_all(trackpoints)
        return

    for tp in trackpoints[:edge]:
        _clear_coords(tp)
    for tp in trackpoints[n - edge:]:
        _clear_coords(tp)
