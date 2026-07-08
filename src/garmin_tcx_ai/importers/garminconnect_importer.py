"""Local Garmin Connect TCX importer.

This module keeps Garmin Connect access optional and local-only. It downloads
TCX files into a local raw-data folder, then the regular pipeline can process
those files through the existing bundle contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import getpass
from pathlib import Path
import re
from typing import Any, Callable


@dataclass(frozen=True)
class GarminConnectImportConfig:
    """Configuration for downloading TCX activities from Garmin Connect."""

    start_date: str
    end_date: str
    activity_type: str = "running"
    download_dir: Path = Path("data/raw/garminconnect")
    email: str | None = None
    limit: int | None = None
    overwrite: bool = False


@dataclass(frozen=True)
class GarminConnectImportResult:
    """Result of a local Garmin Connect TCX import run."""

    success: bool
    downloaded_count: int
    skipped_count: int
    failed_count: int
    download_dir: Path
    tcx_paths: list[Path] = field(default_factory=list)
    warning_messages: list[str] = field(default_factory=list)
    error_message: str | None = None


class GarminConnectDependencyError(RuntimeError):
    """Raised when the optional garminconnect dependency is unavailable."""


def _load_garmin_class() -> type[Any]:
    try:
        from garminconnect import Garmin
    except ImportError as exc:
        raise GarminConnectDependencyError(
            "Error: Optional dependency 'garminconnect' is not installed. "
            "Install it with: uv sync --extra garminconnect"
        ) from exc
    return Garmin


def _prompt_mfa_code() -> str:
    return input("Garmin MFA code: ")


def _create_client(
    garmin_cls: type[Any],
    email: str,
    password: str,
    mfa_callback: Callable[[], str],
) -> Any:
    try:
        return garmin_cls(email, password, prompt_mfa=mfa_callback)
    except TypeError:
        return garmin_cls(email, password)


def _safe_filename_part(value: object, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = text.replace(" ", "T")
    text = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", text)
    text = re.sub(r"-+", "-", text)
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
    return text.strip(".-_") or fallback


def _activity_id(activity: dict[str, Any]) -> str | None:
    value = activity.get("activityId") or activity.get("activity_id")
    if value is None:
        return None
    return str(value)


def _activity_start_time(activity: dict[str, Any]) -> str:
    value = (
        activity.get("startTimeLocal")
        or activity.get("startTimeGMT")
        or activity.get("beginTimestamp")
        or activity.get("start_time")
    )
    text = str(value or "unknown-start").strip()
    text = text.replace("Z", "")
    if "T" not in text and " " in text:
        text = text.replace(" ", "T", 1)
    text = text.replace(":", "-")
    return _safe_filename_part(text, "unknown-start")


def _download_format(garmin_cls: type[Any]) -> Any:
    try:
        return garmin_cls.ActivityDownloadFormat.TCX
    except AttributeError:
        return "TCX"


def _tcx_bytes(downloaded: Any) -> bytes:
    if isinstance(downloaded, bytes):
        return downloaded
    if isinstance(downloaded, str):
        return downloaded.encode("utf-8")
    content = getattr(downloaded, "content", None)
    if isinstance(content, bytes):
        return content
    raise TypeError("Downloaded TCX content is not bytes-like")


def _redact_sensitive_message(message: object) -> str:
    text = str(message)
    text = re.sub(
        r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [REDACTED]",
        text,
    )
    text = re.sub(
        r"(?i)\b(authorization|token|password|cookie)(\s*[:=]\s*)([^\s,;]+)",
        r"\1\2[REDACTED]",
        text,
    )
    return text


def _target_path(
    download_dir: Path,
    activity: dict[str, Any],
    activity_id: str,
    activity_type: str,
) -> Path:
    start_time = _activity_start_time(activity)
    safe_id = _safe_filename_part(activity_id, "unknown-id")
    safe_type = _safe_filename_part(activity_type, "activity")
    filename = f"{start_time}_activity_{safe_id}_{safe_type}.tcx"
    return download_dir / filename


def download_tcx_activities(
    config: GarminConnectImportConfig,
) -> GarminConnectImportResult:
    """Download Garmin Connect activities as local TCX files.

    Args:
        config: Import date range, activity type, destination, and behavior.

    Returns:
        Import result with counts, warnings, and local TCX paths.
    """
    warning_messages: list[str] = []
    tcx_paths: list[Path] = []
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    download_dir = Path(config.download_dir)

    try:
        garmin_cls = _load_garmin_class()
    except GarminConnectDependencyError as exc:
        return GarminConnectImportResult(
            success=False,
            downloaded_count=0,
            skipped_count=0,
            failed_count=0,
            download_dir=download_dir,
            tcx_paths=[],
            warning_messages=[],
            error_message=str(exc),
        )

    email = config.email or input("Garmin email: ")
    password = getpass.getpass("Garmin password: ")

    try:
        client = _create_client(
            garmin_cls,
            email=email,
            password=password,
            mfa_callback=_prompt_mfa_code,
        )
        login = getattr(client, "login", None)
        if callable(login):
            login()
        activities = client.get_activities_by_date(
            config.start_date,
            config.end_date,
            config.activity_type,
            sortorder="asc",
        )
    except Exception as exc:
        return GarminConnectImportResult(
            success=False,
            downloaded_count=0,
            skipped_count=0,
            failed_count=0,
            download_dir=download_dir,
            tcx_paths=[],
            warning_messages=warning_messages,
            error_message=(
                "Error importing from Garmin Connect: "
                f"{_redact_sensitive_message(exc)}"
            ),
        )

    if config.limit is not None:
        activities = activities[: config.limit]

    download_dir.mkdir(parents=True, exist_ok=True)
    tcx_format = _download_format(garmin_cls)

    for activity in activities:
        activity_id = _activity_id(activity)
        if activity_id is None:
            skipped_count += 1
            warning_messages.append(
                "Warning: Skipping Garmin Connect activity without "
                "activityId."
            )
            continue

        target = _target_path(
            download_dir,
            activity=activity,
            activity_id=activity_id,
            activity_type=config.activity_type,
        )
        if target.exists() and not config.overwrite:
            skipped_count += 1
            tcx_paths.append(target)
            continue

        try:
            downloaded = client.download_activity(activity_id, tcx_format)
            target.write_bytes(_tcx_bytes(downloaded))
            downloaded_count += 1
            tcx_paths.append(target)
        except Exception as exc:
            failed_count += 1
            warning_messages.append(
                "Warning: Failed to download Garmin Connect activity "
                f"{activity_id}: {_redact_sensitive_message(exc)}"
            )

    success = bool(tcx_paths)
    error_message = None
    if not success:
        error_message = (
            "Error: No TCX files were downloaded or available in the "
            f"download folder: {download_dir}"
        )

    return GarminConnectImportResult(
        success=success,
        downloaded_count=downloaded_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        download_dir=download_dir,
        tcx_paths=tcx_paths,
        warning_messages=warning_messages,
        error_message=error_message,
    )
