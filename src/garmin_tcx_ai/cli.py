"""CLI module for the Garmin TCX AI tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


from garmin_tcx_ai.importers import (
    GarminConnectImportConfig,
    download_tcx_activities,
)
from garmin_tcx_ai.pipeline import BundleRunConfig, run_bundle


def _run_bundle(args: argparse.Namespace) -> int:
    """Orchestrate parsing, normalizing, and exporting of TCX files.

    Returns:
        0 on success, 1 on failure.
    """
    config = BundleRunConfig(
        input_path=Path(args.input),
        output_dir=Path(args.output),
        gps_policy=args.gps_policy,
        timezone_name=args.timezone,
        max_gap_minutes=args.max_gap_minutes,
        write_atomic=args.write_atomic,
        write_coach_handoff=args.write_coach_handoff,
    )

    result = run_bundle(config)

    for warning in result.warning_messages:
        print(warning, file=sys.stderr)

    if not result.success:
        if result.error_message:
            print(result.error_message, file=sys.stderr)
        return 1

    print(f"Successfully processed {result.activity_count} activities.")
    print(f"Output folder: {result.output_dir.resolve()}")
    return 0


def _run_import_garminconnect(args: argparse.Namespace) -> int:
    """Download Garmin Connect TCX files and run the bundle pipeline.

    Returns:
        0 on success, 1 on failure.
    """
    import_config = GarminConnectImportConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        activity_type=args.activity_type,
        download_dir=Path(args.download_dir),
        email=args.email,
        limit=args.limit,
        overwrite=args.overwrite,
    )
    import_result = download_tcx_activities(import_config)

    for warning in import_result.warning_messages:
        print(warning, file=sys.stderr)

    if not import_result.success:
        if import_result.error_message:
            print(import_result.error_message, file=sys.stderr)
        return 1

    bundle_config = BundleRunConfig(
        input_path=import_result.download_dir,
        output_dir=Path(args.output),
        gps_policy=args.gps_policy,
        timezone_name=args.timezone,
        max_gap_minutes=args.max_gap_minutes,
        write_atomic=args.write_atomic,
        write_coach_handoff=args.write_coach_handoff,
    )
    bundle_result = run_bundle(bundle_config)

    for warning in bundle_result.warning_messages:
        print(warning, file=sys.stderr)

    if not bundle_result.success:
        if bundle_result.error_message:
            print(bundle_result.error_message, file=sys.stderr)
        return 1

    print(f"Downloaded activities: {import_result.downloaded_count}")
    print(f"Skipped activities: {import_result.skipped_count}")
    print(f"Failed activities: {import_result.failed_count}")
    print(f"Download folder: {import_result.download_dir.resolve()}")
    print(f"Processed activities: {bundle_result.activity_count}")
    print(f"Output folder: {bundle_result.output_dir.resolve()}")
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
        help=(
            "Max gap minutes between adjacent activities for "
            "session candidate grouping (default: 30)."
        ),
    )
    bundle_parser.add_argument(
        "--write-atomic",
        action="store_true",
        help="Additionally write per-activity debug/audit artifacts.",
    )
    bundle_parser.add_argument(
        "--write-coach-handoff",
        action="store_true",
        help="Additionally write coach handoff Markdown report.",
    )

    import_parser = subparsers.add_parser(
        "import-garminconnect",
        help=(
            "Download local Garmin Connect TCX files and process a "
            "session bundle."
        ),
    )
    import_parser.add_argument(
        "--start-date",
        required=True,
        help="Start date for Garmin Connect activity import (YYYY-MM-DD).",
    )
    import_parser.add_argument(
        "--end-date",
        required=True,
        help="End date for Garmin Connect activity import (YYYY-MM-DD).",
    )
    import_parser.add_argument(
        "--activity-type",
        default="running",
        help="Garmin Connect activity type to import (default: running).",
    )
    import_parser.add_argument(
        "--download-dir",
        default="data/raw/garminconnect",
        help=(
            "Local folder for downloaded TCX files "
            "(default: data/raw/garminconnect)."
        ),
    )
    import_parser.add_argument(
        "--email",
        help="Garmin Connect email. If omitted, the CLI prompts for it.",
    )
    import_parser.add_argument(
        "--limit",
        type=int,
        help="Optional maximum number of activities to download.",
    )
    import_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing TCX files in the download folder.",
    )
    import_parser.add_argument(
        "--output",
        required=True,
        help="Output directory for the processed files.",
    )
    import_parser.add_argument(
        "--gps-policy",
        default="redact_start_end",
        choices=["keep", "remove", "redact_start_end"],
        help="GPS privacy policy to apply (default: redact_start_end).",
    )
    import_parser.add_argument(
        "--timezone",
        default="Asia/Taipei",
        help="Timezone name for local times (default: Asia/Taipei).",
    )
    import_parser.add_argument(
        "--max-gap-minutes",
        type=int,
        default=30,
        help=(
            "Max gap minutes between adjacent activities for "
            "session candidate grouping (default: 30)."
        ),
    )
    import_parser.add_argument(
        "--write-atomic",
        action="store_true",
        help="Additionally write per-activity debug/audit artifacts.",
    )
    import_parser.add_argument(
        "--write-coach-handoff",
        action="store_true",
        help="Additionally write coach handoff Markdown report.",
    )

    args = parser.parse_args(argv)

    if args.command == "bundle":
        return _run_bundle(args)
    if args.command == "import-garminconnect":
        return _run_import_garminconnect(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
