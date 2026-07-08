"""Credential storage manager using Python keyring.

This module provides utility functions to securely store, retrieve,
delete, and check Garmin Connect credentials in the system's keyring.
It lazy-imports the keyring module so core functions do not crash
if keyring is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

SERVICE_NAME = "garmin-tcx-ai.garminconnect"


@dataclass(frozen=True)
class CredentialStatus:
    """Status representing the result of a credential operation."""

    available: bool
    has_password: bool
    message: str


def _load_keyring() -> tuple[object | None, type[Exception] | None]:
    """Lazy-load the keyring module.

    Returns:
        A tuple of (keyring_module, KeyringError_type) or (None, None).
    """
    try:
        import keyring
        import keyring.errors
        return keyring, keyring.errors.KeyringError
    except ImportError:
        return None, None


def get_stored_password(email: str) -> str | None:
    """Retrieve the stored password for the given email from keyring.

    Args:
        email: The Garmin Connect email address.

    Returns:
        The password string if found, or None if not found or keyring fails.
    """
    keyring, _ = _load_keyring()
    if keyring is None:
        return None
    try:
        return keyring.get_password(SERVICE_NAME, email)  # type: ignore
    except Exception as exc:
        logger.warning("Failed to retrieve password from keyring: %s", exc)
        return None


def set_stored_password(email: str, password: str) -> CredentialStatus:
    """Store the password for the given email in the keyring.

    Args:
        email: The Garmin Connect email address.
        password: The Garmin Connect password.

    Returns:
        CredentialStatus indicating success or failure.
    """
    keyring, _ = _load_keyring()
    if keyring is None:
        return CredentialStatus(
            available=False,
            has_password=False,
            message="錯誤：未安裝 'keyring' 套件。請以 optional dependency 安裝。",
        )
    if not password:
        return CredentialStatus(
            available=True,
            has_password=False,
            message="錯誤：密碼不能為空。",
        )
    try:
        keyring.set_password(SERVICE_NAME, email, password)  # type: ignore
        return CredentialStatus(
            available=True,
            has_password=True,
            message="已成功儲存密碼到系統認證管理員。",
        )
    except Exception as exc:
        # Avoid printing the password. We only mention the exception type/message.
        err_msg = str(exc)
        return CredentialStatus(
            available=True,
            has_password=False,
            message=f"儲存密碼失敗：無法存取系統金鑰庫 ({err_msg})。",
        )


def delete_stored_password(email: str) -> CredentialStatus:
    """Delete the stored password for the given email from the keyring.

    Args:
        email: The Garmin Connect email address.

    Returns:
        CredentialStatus indicating success or failure.
    """
    keyring, _ = _load_keyring()
    if keyring is None:
        return CredentialStatus(
            available=False,
            has_password=False,
            message="錯誤：未安裝 'keyring' 套件。請以 optional dependency 安裝。",
        )
    try:
        keyring.delete_password(SERVICE_NAME, email)  # type: ignore
        return CredentialStatus(
            available=True,
            has_password=False,
            message="已從系統認證管理員中刪除密碼。",
        )
    except Exception as exc:
        err_msg = str(exc)
        return CredentialStatus(
            available=True,
            has_password=False,
            message=f"刪除失敗或密碼不存在：{err_msg}。",
        )


def inspect_stored_password(email: str) -> CredentialStatus:
    """Inspect whether a password exists in the keyring for the given email.

    Args:
        email: The Garmin Connect email address.

    Returns:
        CredentialStatus indicating whether it exists.
    """
    keyring, _ = _load_keyring()
    if keyring is None:
        return CredentialStatus(
            available=False,
            has_password=False,
            message="錯誤：未安裝 'keyring' 套件。請以 optional dependency 安裝。",
        )
    try:
        pwd = keyring.get_password(SERVICE_NAME, email)  # type: ignore
        if pwd is not None:
            return CredentialStatus(
                available=True,
                has_password=True,
                message="系統認證管理員中已存在此帳號的密碼。",
            )
        return CredentialStatus(
            available=True,
            has_password=False,
            message="系統認證管理員中未儲存此帳號的密碼。",
        )
    except Exception as exc:
        err_msg = str(exc)
        return CredentialStatus(
            available=True,
            has_password=False,
            message=f"檢查儲存狀態失敗：{err_msg}。",
        )
