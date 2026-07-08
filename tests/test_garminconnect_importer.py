"""Tests for the optional local Garmin Connect TCX importer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from garmin_tcx_ai.importers.garminconnect_importer import (
    GarminConnectImportConfig,
    download_tcx_activities,
)
import garmin_tcx_ai.importers.garminconnect_importer as importer


class _FakeDownloadFormat:
    TCX = "tcx"


class _FakeGarmin:
    ActivityDownloadFormat = _FakeDownloadFormat
    activities: list[dict[str, Any]] = []
    downloads: dict[str, bytes | Exception] = {}
    instances: list["_FakeGarmin"] = []

    def __init__(
        self,
        email: str,
        password: str,
        prompt_mfa: object | None = None,
    ) -> None:
        self.email = email
        self.password = password
        self.prompt_mfa = prompt_mfa
        self.download_calls: list[tuple[str, str]] = []
        _FakeGarmin.instances.append(self)

    def login(self) -> None:
        return None

    def get_activities_by_date(
        self,
        startdate: str,
        enddate: str,
        activitytype: str,
        sortorder: str = "desc",
    ) -> list[dict[str, Any]]:
        assert startdate == "2026-07-01"
        assert enddate == "2026-07-08"
        assert activitytype
        assert sortorder == "asc"
        return list(_FakeGarmin.activities)

    def download_activity(self, activity_id: str, file_format: str) -> bytes:
        self.download_calls.append((activity_id, file_format))
        result = _FakeGarmin.downloads[activity_id]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def fake_garmin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use a fake Garmin client and avoid real credential prompts."""
    _FakeGarmin.activities = []
    _FakeGarmin.downloads = {}
    _FakeGarmin.instances = []
    monkeypatch.setattr(importer, "_load_garmin_class", lambda: _FakeGarmin)
    monkeypatch.setattr(importer.getpass, "getpass", lambda prompt: "secret")


def _config(download_dir: Path, overwrite: bool = False) -> GarminConnectImportConfig:
    return GarminConnectImportConfig(
        start_date="2026-07-01",
        end_date="2026-07-08",
        activity_type="running",
        download_dir=download_dir,
        email="runner@example.test",
        overwrite=overwrite,
    )


def test_downloads_fake_activity_tcx_bytes(tmp_path: Path) -> None:
    """Importer writes TCX bytes returned by the fake Garmin client."""
    _FakeGarmin.activities = [
        {"activityId": 101, "startTimeLocal": "2026-07-01 06:30:00"}
    ]
    _FakeGarmin.downloads = {"101": b"<TrainingCenterDatabase />"}

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is True
    assert result.downloaded_count == 1
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert len(result.tcx_paths) == 1
    assert result.tcx_paths[0].read_bytes() == b"<TrainingCenterDatabase />"
    assert result.tcx_paths[0].name == (
        "2026-07-01T06-30-00_activity_101_running.tcx"
    )


def test_activity_without_id_is_skipped_with_warning(tmp_path: Path) -> None:
    """Importer skips activities that do not include activityId."""
    _FakeGarmin.activities = [
        {"startTimeLocal": "2026-07-01 06:30:00"},
        {"activityId": 202, "startTimeLocal": "2026-07-02 06:30:00"},
    ]
    _FakeGarmin.downloads = {"202": b"<tcx />"}

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is True
    assert result.downloaded_count == 1
    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert "without activityId" in result.warning_messages[0]


def test_existing_tcx_is_skipped_without_overwrite(tmp_path: Path) -> None:
    """Existing TCX files are reused unless overwrite is requested."""
    _FakeGarmin.activities = [
        {"activityId": 303, "startTimeLocal": "2026-07-03 06:30:00"}
    ]
    _FakeGarmin.downloads = {"303": b"new"}
    existing = tmp_path / "2026-07-03T06-30-00_activity_303_running.tcx"
    existing.write_bytes(b"old")

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is True
    assert result.downloaded_count == 0
    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert result.tcx_paths == [existing]
    assert existing.read_bytes() == b"old"
    assert _FakeGarmin.instances[0].download_calls == []


def test_overwrite_true_rewrites_existing_tcx(tmp_path: Path) -> None:
    """overwrite=True downloads and replaces an existing target file."""
    _FakeGarmin.activities = [
        {"activityId": 404, "startTimeLocal": "2026-07-04 06:30:00"}
    ]
    _FakeGarmin.downloads = {"404": b"new"}
    existing = tmp_path / "2026-07-04T06-30-00_activity_404_running.tcx"
    existing.write_bytes(b"old")

    result = download_tcx_activities(_config(tmp_path, overwrite=True))

    assert result.success is True
    assert result.downloaded_count == 1
    assert result.skipped_count == 0
    assert existing.read_bytes() == b"new"


def test_single_download_failure_warns_and_continues(tmp_path: Path) -> None:
    """One failed download does not stop other activities."""
    _FakeGarmin.activities = [
        {"activityId": 501, "startTimeLocal": "2026-07-05 06:30:00"},
        {"activityId": 502, "startTimeLocal": "2026-07-05 07:30:00"},
    ]
    _FakeGarmin.downloads = {
        "501": RuntimeError("temporary failure"),
        "502": b"<tcx />",
    }

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is True
    assert result.downloaded_count == 1
    assert result.failed_count == 1
    assert len(result.tcx_paths) == 1
    assert "501" in result.warning_messages[0]


def test_empty_tcx_download_is_failed_without_writing_file(
    tmp_path: Path,
) -> None:
    """Empty downloaded TCX content is treated as a failed activity."""
    _FakeGarmin.activities = [
        {"activityId": 503, "startTimeLocal": "2026-07-05 08:30:00"}
    ]
    _FakeGarmin.downloads = {"503": b"  \n\t"}

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is False
    assert result.downloaded_count == 0
    assert result.failed_count == 1
    assert result.tcx_paths == []
    assert "Downloaded TCX content is empty" in result.warning_messages[0]
    assert not list(tmp_path.glob("*.tcx"))


def test_download_failure_warning_redacts_sensitive_text(
    tmp_path: Path,
) -> None:
    """Importer warnings redact token-like exception details."""
    _FakeGarmin.activities = [
        {"activityId": 503, "startTimeLocal": "2026-07-05 08:30:00"}
    ]
    _FakeGarmin.downloads = {
        "503": RuntimeError("Authorization: Bearer abc123 token=secret")
    }

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is False
    assert "abc123" not in result.warning_messages[0]
    assert "secret" not in result.warning_messages[0]
    assert "[REDACTED]" in result.warning_messages[0]


def test_non_positive_limit_returns_error_without_login(
    tmp_path: Path,
) -> None:
    """Importer rejects non-positive limits before creating a client."""
    result = download_tcx_activities(
        GarminConnectImportConfig(
            start_date="2026-07-01",
            end_date="2026-07-08",
            download_dir=tmp_path,
            email="runner@example.test",
            limit=0,
        )
    )

    assert result.success is False
    assert result.error_message == "Error: limit must be a positive integer."
    assert result.downloaded_count == 0
    assert result.skipped_count == 0
    assert result.failed_count == 0
    assert _FakeGarmin.instances == []


def test_all_downloads_fail_returns_success_false(tmp_path: Path) -> None:
    """Importer fails clearly when no TCX file can be used."""
    _FakeGarmin.activities = [
        {"activityId": 601, "startTimeLocal": "2026-07-06 06:30:00"}
    ]
    _FakeGarmin.downloads = {"601": RuntimeError("download failed")}

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is False
    assert result.downloaded_count == 0
    assert result.failed_count == 1
    assert result.tcx_paths == []
    assert result.error_message is not None
    assert "No TCX files" in result.error_message


def test_filename_is_windows_safe(tmp_path: Path) -> None:
    """Generated TCX filenames do not contain Windows-illegal characters."""
    config = GarminConnectImportConfig(
        start_date="2026-07-01",
        end_date="2026-07-08",
        activity_type='run/type:*?"<>|',
        download_dir=tmp_path,
        email="runner@example.test",
    )
    _FakeGarmin.activities = [
        {"activityId": 'abc:*?"<>|', "startTimeLocal": "2026-07-07 06:30:00"}
    ]
    _FakeGarmin.downloads = {'abc:*?"<>|': b"<tcx />"}

    result = download_tcx_activities(config)

    assert result.success is True
    filename = result.tcx_paths[0].name
    assert all(char not in filename for char in '<>:"/\\|?*')
    assert filename.endswith(".tcx")


def test_missing_optional_dependency_returns_clear_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The importer can fail without importing garminconnect at test time."""
    def raise_missing() -> type[Any]:
        raise importer.GarminConnectDependencyError("install optional extra")

    monkeypatch.setattr(importer, "_load_garmin_class", raise_missing)

    result = download_tcx_activities(_config(tmp_path))

    assert result.success is False
    assert result.error_message == "install optional extra"


def test_download_uses_password_provider_if_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that download_tcx_activities queries the password provider if passed."""
    conf = GarminConnectImportConfig(
        start_date="2026-07-01",
        end_date="2026-07-08",
        activity_type="running",
        download_dir=tmp_path,
        email="runner@example.test",
    )
    _FakeGarmin.activities = [
        {"activityId": 101, "startTimeLocal": "2026-07-01 06:30:00"}
    ]
    _FakeGarmin.downloads = {"101": b"<TrainingCenterDatabase />"}

    monkeypatch.delattr(importer.getpass, "getpass", raising=False)

    called_provider = False
    def mock_provider(email: str) -> str:
        nonlocal called_provider
        called_provider = True
        assert email == "runner@example.test"
        return "provider_password"

    result = download_tcx_activities(conf, password_provider=mock_provider)
    assert result.success is True
    assert called_provider is True
    assert _FakeGarmin.instances[0].password == "provider_password"


def test_download_uses_config_password_directly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that download_tcx_activities uses the config password directly without prompting."""
    conf = GarminConnectImportConfig(
        start_date="2026-07-01",
        end_date="2026-07-08",
        activity_type="running",
        download_dir=tmp_path,
        email="runner@example.test",
        password="direct_password",
    )
    _FakeGarmin.activities = [
        {"activityId": 101, "startTimeLocal": "2026-07-01 06:30:00"}
    ]
    _FakeGarmin.downloads = {"101": b"<TrainingCenterDatabase />"}

    monkeypatch.delattr(importer.getpass, "getpass", raising=False)

    result = download_tcx_activities(conf)
    assert result.success is True
    assert _FakeGarmin.instances[0].password == "direct_password"


def test_download_empty_password_fails_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that empty password returns a structured failure without login attempt."""
    conf = GarminConnectImportConfig(
        start_date="2026-07-01",
        end_date="2026-07-08",
        activity_type="running",
        download_dir=tmp_path,
        email="runner@example.test",
        password="",
    )
    monkeypatch.setattr(importer.getpass, "getpass", lambda prompt: "")

    result = download_tcx_activities(conf)
    assert result.success is False
    assert "password must not be empty" in result.error_message
    assert not _FakeGarmin.instances
