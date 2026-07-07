"""CLI module for the Garmin TCX AI tool."""

from __future__ import annotations

import argparse
import sys
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
from garmin_tcx_ai.normalizer import normalize_activity
from garmin_tcx_ai.parser import (
    TCXParseError,
    UnsupportedActivityError,
    parse_tcx,
)


def _run_bundle(args: argparse.Namespace) -> int:
    """Orchestrate parsing, normalizing, and exporting of TCX files.

    Returns:
        0 on success, 1 on failure.
    """
    input_path = Path(args.input)
    output_dir = Path(args.output)

    # 1. Validate input path exists
    if not input_path.exists():
        print(
            f"Error: Input path does not exist: {input_path}",
            file=sys.stderr,
        )
        return 1

    # 2. Gather TCX files
    tcx_files: list[Path] = []
    if input_path.is_dir():
        # First-level only, case-insensitive check
        for path in input_path.iterdir():
            if path.is_file() and path.suffix.lower() == ".tcx":
                tcx_files.append(path)

        if not tcx_files:
            print(
                f"Error: No .tcx files found in directory: {input_path}",
                file=sys.stderr,
            )
            return 1
    else:
        tcx_files.append(input_path)

    # 3. Validate timezone early
    try:
        try:
            ZoneInfo(args.timezone)
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            if args.timezone not in ("Asia/Taipei", "UTC"):
                raise ValueError
    except ValueError:
        print(
            f"Error: Invalid timezone name: {args.timezone}",
            file=sys.stderr,
        )
        return 1

    # 4. Validate max_gap_minutes
    if args.max_gap_minutes < 0:
        print(
            "Error: max-gap-minutes must be greater than or equal to 0",
            file=sys.stderr,
        )
        return 1

    # 5. Parse and normalize activities
    normalized_activities = []
    is_dir = input_path.is_dir()
    for file_path in tcx_files:
        try:
            parsed = parse_tcx(file_path)
            normalized = normalize_activity(parsed, gps_policy=args.gps_policy)
            normalized_activities.append(normalized)
        except FileNotFoundError as exc:
            if is_dir:
                print(f"Warning: File not found: {exc}", file=sys.stderr)
            else:
                print(f"Error: File not found: {exc}", file=sys.stderr)
                return 1
        except TCXParseError as exc:
            if is_dir:
                print(
                    f"Warning parsing TCX in '{file_path.name}': {exc}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Error parsing TCX in '{file_path.name}': {exc}",
                    file=sys.stderr,
                )
                return 1
        except UnsupportedActivityError as exc:
            if is_dir:
                print(
                    f"Warning: Unsupported activity in '{file_path.name}': {exc}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Error: Unsupported activity in '{file_path.name}': {exc}",
                    file=sys.stderr,
                )
                return 1

    if not normalized_activities:
        print(
            f"Error: No valid TCX activities parsed from input: {input_path}",
            file=sys.stderr,
        )
        return 1

    # 6. Ensure output directory is created
    output_dir.mkdir(parents=True, exist_ok=True)

    # 7. Write session bundle
    try:
        write_session_bundle_json(
            normalized_activities,
            output_dir,
            max_gap_minutes=args.max_gap_minutes,
            timezone_name=args.timezone,
        )
        write_session_bundle_markdown(
            normalized_activities,
            output_dir,
            max_gap_minutes=args.max_gap_minutes,
            timezone_name=args.timezone,
        )
    except ValueError as exc:
        print(f"Error building session bundle: {exc}", file=sys.stderr)
        return 1

    # 8. Write atomic if requested
    if args.write_atomic:
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

            write_activity_json(activity, target_dir)
            write_trackpoints_csv(activity, target_dir)
            write_ai_summary_json(activity, target_dir)
            write_ai_summary_markdown(activity, target_dir)

    # 9. Print success summary
    print(
        f"Successfully processed {len(normalized_activities)} activities."
    )
    print(f"Output folder: {output_dir.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point for garmin-tcx-ai."""
    parser = argparse.ArgumentParser(
        prog="garmin-tcx-ai",
        description="Garmin TCX AI session bundle CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bundle_parser = subparsers.add_parser(
        "bundle",
        help="Convert Garmin TCX files to a session bundle.",
    )
    bundle_parser.add_argument(
        "--input",
        required=True,
        help="Path to a single .tcx file or a directory containing .tcx.",
    )
    bundle_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for the processed files.",
    )
    bundle_parser.add_argument(
        "--gps-policy",
        default="redact_start_end",
        choices=["keep", "remove", "redact_start_end"],
        help="GPS privacy policy to apply (default: redact_start_end).",
    )
    bundle_parser.add_argument(
        "--timezone",
        default="Asia/Taipei",
        help="Timezone name for local times (default: Asia/Taipei).",
    )
    bundle_parser.add_argument(
        "--max-gap-minutes",
        type=int,
        default=30,
        help="Max gap minutes between trackpoints (default: 30).",
    )
    bundle_parser.add_argument(
        "--write-atomic",
        action="store_true",
        help="Additionally write per-activity debug/audit artifacts.",
    )

    args = parser.parse_args(argv)

    if args.command == "bundle":
        return _run_bundle(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
