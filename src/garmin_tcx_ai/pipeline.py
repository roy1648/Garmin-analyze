"""Pipeline module for running Garmin TCX processing bundles."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from garmin_tcx_ai.exporters import (
    safe_activity_id,
    write_activity_json,
    write_ai_summary_json,
    write_ai_summary_markdown,
    write_session_bundle_json,
    write_session_bundle_markdown,
    write_trackpoints_csv,
)
from garmin_tcx_ai.handoff import write_coach_handoff_markdown
from garmin_tcx_ai.normalizer import normalize_activity
from garmin_tcx_ai.parser import (
    TCXParseError,
    UnsupportedActivityError,
    parse_tcx,
)


@dataclass(frozen=True)
class BundleRunConfig:
    """Configuration for running a TCX bundle conversion."""

    input_path: Path
    output_dir: Path
    gps_policy: str = "redact_start_end"
    timezone_name: str = "Asia/Taipei"
    max_gap_minutes: int = 30
    write_atomic: bool = False
    write_coach_handoff: bool = False


@dataclass(frozen=True)
class BundleRunResult:
    """Result of running a TCX bundle conversion."""

    success: bool
    activity_count: int
    output_dir: Path
    warning_messages: list[str]
    error_message: str | None = None
    session_bundle_json_path: Path | None = None
    session_bundle_markdown_path: Path | None = None
    coach_handoff_markdown_path: Path | None = None
    atomic_artifact_paths: list[Path] = field(default_factory=list)


def run_bundle(config: BundleRunConfig) -> BundleRunResult:
    """Orchestrate parsing, normalizing, and exporting of TCX files.

    Args:
        config: The BundleRunConfig parameters.

    Returns:
        BundleRunResult with success status, counts, warning/error messages
        and written paths.
    """
    input_path = config.input_path
    output_dir = config.output_dir
    warning_messages: list[str] = []

    # 1. Validate input path exists
    if not input_path.exists():
        return BundleRunResult(
            success=False,
            activity_count=0,
            output_dir=output_dir,
            warning_messages=warning_messages,
            error_message=f"Error: Input path does not exist: {input_path}",
        )

    # 2. Gather TCX files
    tcx_files: list[Path] = []
    if input_path.is_dir():
        # First-level only, case-insensitive check
        for path in input_path.iterdir():
            if path.is_file() and path.suffix.lower() == ".tcx":
                tcx_files.append(path)

        if not tcx_files:
            return BundleRunResult(
                success=False,
                activity_count=0,
                output_dir=output_dir,
                warning_messages=warning_messages,
                error_message=(
                    f"Error: No .tcx files found in directory: {input_path}"
                ),
            )
    else:
        tcx_files.append(input_path)

    # 3. Validate timezone early
    try:
        try:
            ZoneInfo(config.timezone_name)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            if config.timezone_name not in ("Asia/Taipei", "UTC"):
                raise ValueError
    except ValueError:
        return BundleRunResult(
            success=False,
            activity_count=0,
            output_dir=output_dir,
            warning_messages=warning_messages,
            error_message=(
                f"Error: Invalid timezone name: {config.timezone_name}"
            ),
        )

    # 4. Validate max_gap_minutes
    if config.max_gap_minutes < 0:
        return BundleRunResult(
            success=False,
            activity_count=0,
            output_dir=output_dir,
            warning_messages=warning_messages,
            error_message=(
                "Error: max-gap-minutes must be greater than or equal to 0"
            ),
        )

    # 5. Parse and normalize activities
    normalized_activities = []
    is_dir = input_path.is_dir()
    for file_path in tcx_files:
        try:
            parsed = parse_tcx(file_path)
            normalized = normalize_activity(
                parsed, gps_policy=config.gps_policy
            )
            normalized_activities.append(normalized)
        except FileNotFoundError as exc:
            if is_dir:
                warning_messages.append(f"Warning: File not found: {exc}")
            else:
                return BundleRunResult(
                    success=False,
                    activity_count=0,
                    output_dir=output_dir,
                    warning_messages=warning_messages,
                    error_message=f"Error: File not found: {exc}",
                )
        except TCXParseError as exc:
            if is_dir:
                warning_messages.append(
                    f"Warning parsing TCX in '{file_path.name}': {exc}"
                )
            else:
                return BundleRunResult(
                    success=False,
                    activity_count=0,
                    output_dir=output_dir,
                    warning_messages=warning_messages,
                    error_message=(
                        f"Error parsing TCX in '{file_path.name}': {exc}"
                    ),
                )
        except UnsupportedActivityError as exc:
            if is_dir:
                warning_messages.append(
                    f"Warning: Unsupported activity in '{file_path.name}': "
                    f"{exc}"
                )
            else:
                return BundleRunResult(
                    success=False,
                    activity_count=0,
                    output_dir=output_dir,
                    warning_messages=warning_messages,
                    error_message=(
                        f"Error: Unsupported activity in '{file_path.name}': "
                        f"{exc}"
                    ),
                )

    if not normalized_activities:
        return BundleRunResult(
            success=False,
            activity_count=0,
            output_dir=output_dir,
            warning_messages=warning_messages,
            error_message=(
                f"Error: No valid TCX activities parsed from input: "
                f"{input_path}"
            ),
        )

    # 6. Ensure output directory is created
    output_dir.mkdir(parents=True, exist_ok=True)

    # 7. Write session bundle
    try:
        sb_json = write_session_bundle_json(
            normalized_activities,
            output_dir,
            max_gap_minutes=config.max_gap_minutes,
            timezone_name=config.timezone_name,
        )
        sb_md = write_session_bundle_markdown(
            normalized_activities,
            output_dir,
            max_gap_minutes=config.max_gap_minutes,
            timezone_name=config.timezone_name,
        )
        ch_md = None
        if config.write_coach_handoff:
            ch_md = write_coach_handoff_markdown(
                normalized_activities,
                output_dir,
                max_gap_minutes=config.max_gap_minutes,
                timezone_name=config.timezone_name,
            )
    except ValueError as exc:
        return BundleRunResult(
            success=False,
            activity_count=0,
            output_dir=output_dir,
            warning_messages=warning_messages,
            error_message=f"Error building session bundle: {exc}",
        )

    # 8. Write atomic if requested
    atomic_paths: list[Path] = []
    if config.write_atomic:
        seen_ids = {}
        for activity in normalized_activities:
            sid = safe_activity_id(
                activity.activity.activity_id,
                activity.source.file_name,
            )
            seen_ids[sid] = seen_ids.get(sid, 0) + 1

        collision_ids = {
            sid for sid, count in seen_ids.items() if count > 1
        }

        seen_dirs = set()
        for activity in normalized_activities:
            sid = safe_activity_id(
                activity.activity.activity_id,
                activity.source.file_name,
            )
            if sid in collision_ids:
                stem = (
                    Path(activity.source.file_name).stem
                    if activity.source.file_name
                    else "activity"
                )
                safe_stem = safe_activity_id(stem)
                candidate_dir = output_dir / safe_stem
                counter = 1
                while candidate_dir in seen_dirs:
                    candidate_dir = output_dir / f"{safe_stem}_{counter}"
                    counter += 1
                target_dir = candidate_dir
            else:
                target_dir = output_dir

            seen_dirs.add(target_dir)

            p1 = write_activity_json(activity, target_dir)
            p2 = write_trackpoints_csv(activity, target_dir)
            p3 = write_ai_summary_json(activity, target_dir)
            p4 = write_ai_summary_markdown(activity, target_dir)
            atomic_paths.extend([p1, p2, p3, p4])

    return BundleRunResult(
        success=True,
        activity_count=len(normalized_activities),
        output_dir=output_dir,
        warning_messages=warning_messages,
        session_bundle_json_path=sb_json,
        session_bundle_markdown_path=sb_md,
        coach_handoff_markdown_path=ch_md,
        atomic_artifact_paths=atomic_paths,
    )
