"""Tests for GPS privacy policy handling."""

from __future__ import annotations

from garmin_tcx_ai.models import (
    Activity,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
)
from garmin_tcx_ai.privacy import apply_gps_policy


def _make_activity(trackpoints: list[Trackpoint]) -> ParsedActivity:
    """Build a minimal ParsedActivity for privacy tests."""
    return ParsedActivity(
        source=SourceInfo(
            format="tcx",
            file_name="a.tcx",
            file_path="a.tcx",
        ),
        privacy=PrivacyInfo(gps_policy="keep"),
        activity=Activity(sport="Running", activity_id="id"),
        laps=[],
        trackpoints=trackpoints,
    )


def _points_with_distance(
    distances: list[float],
) -> list[Trackpoint]:
    """Build trackpoints with cumulative distances and dummy coordinates."""
    return [
        Trackpoint(
            trackpoint_index=i + 1,
            lap_index=1,
            latitude=10.0 + i * 0.001,
            longitude=20.0 + i * 0.001,
            distance_meters=d,
        )
        for i, d in enumerate(distances)
    ]


def test_keep_preserves_coordinates() -> None:
    """`keep` leaves every latitude/longitude untouched."""
    pts = _points_with_distance([0.0, 100.0, 200.0])
    result = apply_gps_policy(_make_activity(pts), "keep")
    assert result.privacy.gps_policy == "keep"
    assert all(tp.latitude is not None for tp in result.trackpoints)
    assert all(tp.longitude is not None for tp in result.trackpoints)


def test_remove_nulls_all_coordinates() -> None:
    """`remove` sets every latitude/longitude to None."""
    pts = _points_with_distance([0.0, 100.0, 200.0])
    result = apply_gps_policy(_make_activity(pts), "remove")
    assert result.privacy.gps_policy == "remove"
    assert all(tp.latitude is None for tp in result.trackpoints)
    assert all(tp.longitude is None for tp in result.trackpoints)


def test_does_not_mutate_input() -> None:
    """The source activity is never mutated by apply_gps_policy."""
    pts = _points_with_distance([0.0, 100.0, 200.0])
    original = _make_activity(pts)
    apply_gps_policy(original, "remove")
    assert all(tp.latitude is not None for tp in original.trackpoints)
    assert original.privacy.gps_policy == "keep"


def test_redact_start_end_by_distance() -> None:
    """With distance data, first 300m and last 300m are redacted."""
    # Distances 0..1000 in 100m steps -> total 1000m.
    pts = _points_with_distance([float(d) for d in range(0, 1001, 100)])
    result = apply_gps_policy(_make_activity(pts), "redact_start_end")

    for tp in result.trackpoints:
        d = tp.distance_meters
        if d <= 300.0 or d >= 700.0:
            assert tp.latitude is None
            assert tp.longitude is None
        else:
            # Middle segment (400, 500, 600) is preserved.
            assert tp.latitude is not None
            assert tp.longitude is not None


def test_redact_start_end_fallback_by_count() -> None:
    """Without usable distance data, first/last 10% of points are redacted."""
    # 20 trackpoints, no distance_meters -> fallback to fraction (edge = 2).
    pts = [
        Trackpoint(
            trackpoint_index=i + 1,
            lap_index=1,
            latitude=10.0 + i * 0.001,
            longitude=20.0 + i * 0.001,
        )
        for i in range(20)
    ]
    result = apply_gps_policy(_make_activity(pts), "redact_start_end")
    tps = result.trackpoints

    # First 2 and last 2 redacted; middle preserved.
    assert tps[0].latitude is None and tps[1].latitude is None
    assert tps[-1].latitude is None and tps[-2].latitude is None
    assert all(tp.latitude is not None for tp in tps[2:-2])


def test_redact_start_end_fallback_rounds_up_to_cover_fraction() -> None:
    """Fallback redacts at least 10% at each end (ceil), e.g. 19 -> 2."""
    pts = [
        Trackpoint(
            trackpoint_index=i + 1,
            lap_index=1,
            latitude=10.0 + i * 0.001,
            longitude=20.0 + i * 0.001,
        )
        for i in range(19)
    ]
    result = apply_gps_policy(_make_activity(pts), "redact_start_end")
    tps = result.trackpoints

    # ceil(19 * 0.1) = 2 redacted at each end.
    assert tps[0].latitude is None and tps[1].latitude is None
    assert tps[-1].latitude is None and tps[-2].latitude is None
    assert tps[2].latitude is not None
    assert tps[-3].latitude is not None


def test_redact_start_end_sparse_distance_uses_count_fallback() -> None:
    """Sparse distance data (some points missing) uses the count fallback.

    Only a few points carry distance; the distance-based branch would leak
    early points whose first recorded distance already exceeds 300m, so the
    fraction fallback must be used instead.
    """
    pts = []
    for i in range(20):
        # Only every 5th point has a (large) cumulative distance.
        dist = float(400 + i * 100) if i % 5 == 0 else None
        pts.append(
            Trackpoint(
                trackpoint_index=i + 1,
                lap_index=1,
                latitude=10.0 + i * 0.001,
                longitude=20.0 + i * 0.001,
                distance_meters=dist,
            )
        )
    result = apply_gps_policy(_make_activity(pts), "redact_start_end")
    tps = result.trackpoints

    # Fallback edge = floor(20 * 0.1) = 2: first 2 and last 2 redacted.
    assert tps[0].latitude is None and tps[1].latitude is None
    assert tps[-1].latitude is None and tps[-2].latitude is None
    assert all(tp.latitude is not None for tp in tps[2:-2])


def test_redact_start_end_distance_not_starting_at_zero() -> None:
    """Windows anchor to the min distance when the run does not start at 0."""
    # Distances 500..1500 (span 1000) -> redact <=800 and >=1200.
    pts = _points_with_distance([float(d) for d in range(500, 1501, 100)])
    result = apply_gps_policy(_make_activity(pts), "redact_start_end")
    for tp in result.trackpoints:
        d = tp.distance_meters
        if d <= 800.0 or d >= 1200.0:
            assert tp.latitude is None
        else:
            assert tp.latitude is not None


def test_redact_start_end_short_activity_redacts_all_by_distance() -> None:
    """A short activity (<=600m total) has all coordinates redacted."""
    pts = _points_with_distance([0.0, 100.0, 200.0, 400.0])
    result = apply_gps_policy(_make_activity(pts), "redact_start_end")
    assert all(tp.latitude is None for tp in result.trackpoints)
    assert all(tp.longitude is None for tp in result.trackpoints)


def test_redact_start_end_short_activity_redacts_all_by_count() -> None:
    """Too few points for a middle segment redacts all (fallback path)."""
    pts = [
        Trackpoint(
            trackpoint_index=i + 1,
            lap_index=1,
            latitude=10.0 + i,
            longitude=20.0 + i,
        )
        for i in range(2)
    ]
    result = apply_gps_policy(_make_activity(pts), "redact_start_end")
    assert all(tp.latitude is None for tp in result.trackpoints)
