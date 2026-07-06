"""Exporters for normalized Garmin TCX activities.

This module writes the data-contract output files for a normalized
:class:`ParsedActivity`:

* ``activity.json`` -- complete structured activity record.
* ``trackpoints.csv`` -- flat UTF-8 CSV of trackpoint data.
* ``ai_summary.json`` -- structured AI-ready factual summary.
* ``ai_summary.md`` -- concise AI-ready Markdown summary.

Both files are written into a per-activity folder whose name is a
path-safe identifier derived from the activity id or source file name.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from garmin_tcx_ai.models import ParsedActivity
from garmin_tcx_ai.summary import (
    build_ai_summary,
    render_ai_summary_markdown,
)

# Characters that are unsafe in Windows and POSIX path components.
_UNSAFE_CHARS = '<>:"/\\|?*'

# CSV header order, mandated by docs/02_data_contract.md.
CSV_COLUMNS = [
    "activity_id",
    "lap_index",
    "trackpoint_index",
    "timestamp",
    "latitude",
    "longitude",
    "altitude_meters",
    "distance_meters",
    "heart_rate_bpm",
    "speed_mps",
    "pace_seconds_per_km",
    "run_cadence_spm",
    "power_watts",
]


def safe_activity_id(
    activity_id: str | None,
    source_file_name: str | None = None,
) -> str:
    """Return a path-safe folder name derived from *activity_id*.

    Path-unsafe characters (``< > : " / \\ | ? *``) are replaced with ``_``.
    Leading/trailing whitespace and trailing dots are stripped. If the result
    is empty, the stem of *source_file_name* is used as a fallback; if that is
    also empty, ``"activity"`` is returned.
    """
    safe = _sanitize_component(activity_id or "")
    if safe:
        return safe

    if source_file_name:
        stem = Path(source_file_name).stem
        safe = _sanitize_component(stem)
        if safe:
            return safe

    return "activity"


def _sanitize_component(value: str) -> str:
    """Sanitize a single path component per the data contract rules."""
    cleaned = "".join(
        "_" if ch in _UNSAFE_CHARS else ch for ch in value
    )
    # Strip surrounding whitespace and any trailing dots/whitespace.
    cleaned = cleaned.strip()
    cleaned = cleaned.rstrip(". ")
    return cleaned


def _output_folder(activity: ParsedActivity, output_dir: Path) -> Path:
    """Create and return the per-activity output folder."""
    folder_name = safe_activity_id(
        activity.activity.activity_id,
        activity.source.file_name,
    )
    folder = Path(output_dir) / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _iso(value: datetime) -> str:
    """Serialize a datetime to an ISO 8601 UTC string with a ``Z`` suffix."""
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _json_default(value: Any) -> Any:
    """JSON serialization hook for datetime values."""
    if isinstance(value, datetime):
        return _iso(value)
    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def write_activity_json(
    activity: ParsedActivity,
    output_dir: Path,
) -> Path:
    """Write ``activity.json`` for a normalized activity.

    The JSON contains the top-level keys ``source``, ``privacy``,
    ``activity``, ``laps``, ``trackpoints``, and ``warnings``. ``None`` values
    are emitted as JSON ``null`` and ``datetime`` values as ISO 8601 strings.
    Returns the path to the written file.
    """
    folder = _output_folder(activity, output_dir)
    payload = {
        "source": asdict(activity.source),
        "privacy": asdict(activity.privacy),
        "activity": asdict(activity.activity),
        "laps": [asdict(lap) for lap in activity.laps],
        "trackpoints": [asdict(tp) for tp in activity.trackpoints],
        "warnings": [asdict(w) for w in activity.warnings],
    }

    target = folder / "activity.json"
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(
            payload,
            fh,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
        fh.write("\n")
    return target


def write_ai_summary_json(
    activity: ParsedActivity,
    output_dir: Path,
) -> Path:
    """Write ``ai_summary.json`` for a normalized activity.

    The JSON is the :func:`build_ai_summary` payload: top-level keys
    ``activity_summary``, ``key_metrics``, ``lap_summary``,
    ``trend_summary``, ``privacy``, ``data_quality`` and ``ai_context``.
    ``None`` values are emitted as JSON ``null`` and ``datetime`` values
    as ISO 8601 strings. Returns the path to the written file.
    """
    folder = _output_folder(activity, output_dir)
    summary = build_ai_summary(activity)

    target = folder / "ai_summary.json"
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(
            summary,
            fh,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
        fh.write("\n")
    return target


def write_ai_summary_markdown(
    activity: ParsedActivity,
    output_dir: Path,
) -> Path:
    """Write ``ai_summary.md`` for a normalized activity.

    The UTF-8 Markdown document is rendered by
    :func:`render_ai_summary_markdown` from the
    :func:`build_ai_summary` payload and never contains GPS coordinates
    or route details. Returns the path to the written file.
    """
    folder = _output_folder(activity, output_dir)
    text = render_ai_summary_markdown(build_ai_summary(activity))

    target = folder / "ai_summary.md"
    target.write_text(text, encoding="utf-8", newline="\n")
    return target


def _cell(value: Any) -> str:
    """Convert a field value to a CSV cell string (``None`` -> empty)."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return _iso(value)
    return str(value)


def write_trackpoints_csv(
    activity: ParsedActivity,
    output_dir: Path,
) -> Path:
    """Write ``trackpoints.csv`` for a normalized activity.

    The CSV is UTF-8 encoded with a header row matching
    ``docs/02_data_contract.md``. Missing values become empty cells and GPS
    columns reflect the currently applied privacy policy. Returns the path to
    the written file.
    """
    folder = _output_folder(activity, output_dir)
    activity_id = activity.activity.activity_id

    target = folder / "trackpoints.csv"
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for tp in activity.trackpoints:
            writer.writerow(
                [
                    _cell(activity_id),
                    _cell(tp.lap_index),
                    _cell(tp.trackpoint_index),
                    _cell(tp.timestamp),
                    _cell(tp.latitude),
                    _cell(tp.longitude),
                    _cell(tp.altitude_meters),
                    _cell(tp.distance_meters),
                    _cell(tp.heart_rate_bpm),
                    _cell(tp.speed_mps),
                    _cell(tp.pace_seconds_per_km),
                    _cell(tp.run_cadence_spm),
                    _cell(tp.power_watts),
                ]
            )
    return target
