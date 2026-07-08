"""Unit tests for credentials storage using python keyring."""

from __future__ import annotations

import pytest

import garmin_tcx_ai.credentials as creds
from garmin_tcx_ai.credentials import (
    get_stored_password,
    set_stored_password,
    delete_stored_password,
    inspect_stored_password,
)


class FakeKeyringModule:
    """Mock keyring module for testing storage interactions."""

    class errors:
        class KeyringError(Exception):
            pass

    def __init__(self) -> None:
        self.storage: dict[tuple[str, str], str] = {}
        self.should_raise: Exception | None = None

    def get_password(self, service: str, username: str) -> str | None:
        if self.should_raise:
            raise self.should_raise
        return self.storage.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        if self.should_raise:
            raise self.should_raise
        self.storage[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if self.should_raise:
            raise self.should_raise
        key = (service, username)
        if key not in self.storage:
            raise self.errors.KeyringError("Password not found")
        del self.storage[key]


def test_credentials_when_keyring_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that credentials functions fall back gracefully when keyring is not installed."""
    monkeypatch.setattr(creds, "_load_keyring", lambda: (None, None))

    assert get_stored_password("test@example.com") is None

    status_set = set_stored_password("test@example.com", "mypassword")
    assert not status_set.available
    assert not status_set.has_password
    assert "keyring" in status_set.message

    status_del = delete_stored_password("test@example.com")
    assert not status_del.available
    assert "keyring" in status_del.message

    status_inspect = inspect_stored_password("test@example.com")
    assert not status_inspect.available
    assert "keyring" in status_inspect.message


def test_credentials_flow_with_fake_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test standard flow (get, set, inspect, delete) using a mock keyring."""
    fake_kr = FakeKeyringModule()
    monkeypatch.setattr(
        creds, "_load_keyring", lambda: (fake_kr, fake_kr.errors.KeyringError)
    )

    # Initially not stored
    inspect_status = inspect_stored_password("test@example.com")
    assert inspect_status.available
    assert not inspect_status.has_password
    assert "未儲存" in inspect_status.message

    # Set password
    set_status = set_stored_password("test@example.com", "secret_pass")
    assert set_status.available
    assert set_status.has_password
    assert "成功" in set_status.message

    # Get password
    pwd = get_stored_password("test@example.com")
    assert pwd == "secret_pass"

    # Inspect password
    inspect_status2 = inspect_stored_password("test@example.com")
    assert inspect_status2.available
    assert inspect_status2.has_password
    assert "已存在" in inspect_status2.message

    # Delete password
    del_status = delete_stored_password("test@example.com")
    assert del_status.available
    assert not del_status.has_password
    assert "刪除" in del_status.message

    # Verify deleted
    assert get_stored_password("test@example.com") is None


def test_credentials_handles_exceptions_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that keyring exceptions are caught and return friendly status without leakage."""
    fake_kr = FakeKeyringModule()
    fake_kr.should_raise = fake_kr.errors.KeyringError("Access Denied")
    monkeypatch.setattr(
        creds, "_load_keyring", lambda: (fake_kr, fake_kr.errors.KeyringError)
    )

    # get_stored_password catches exception and returns None
    assert get_stored_password("test@example.com") is None

    # set_stored_password catches exception, does not include password in message
    set_status = set_stored_password("test@example.com", "secret_pass")
    assert set_status.available
    assert not set_status.has_password
    assert "Access Denied" in set_status.message
    assert "secret_pass" not in set_status.message

    # inspect_stored_password catches exception
    inspect_status = inspect_stored_password("test@example.com")
    assert inspect_status.available
    assert not inspect_status.has_password
    assert "Access Denied" in inspect_status.message

    # delete_stored_password catches exception
    del_status = delete_stored_password("test@example.com")
    assert del_status.available
    assert not del_status.has_password
    assert "Access Denied" in del_status.message


def test_set_stored_password_empty_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test set_stored_password checks for empty password inputs."""
    fake_kr = FakeKeyringModule()
    monkeypatch.setattr(
        creds, "_load_keyring", lambda: (fake_kr, fake_kr.errors.KeyringError)
    )
    status = set_stored_password("test@example.com", "")
    assert status.available
    assert not status.has_password
    assert "為空" in status.message
