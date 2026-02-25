"""
Critical unit tests for SecretsManagerClient.

Covers the six highest-risk paths: JWT cache expiry boundary, token refresh
buffer, credential preservation during JWT writes, correct Secrets Manager
call arguments, AWSPENDING promotion integrity, and graceful None return
when no pending version exists.
"""

import json
import time
from unittest.mock import Mock, call, patch

import pytest
from botocore.exceptions import ClientError

from src.oauth_jwt_service.service.secret_manager_client import SecretsManagerClient
from src.oauth_jwt_service.models.schemas import OAuthCredentials
from src.oauth_jwt_service.config.env import TOKEN_REFRESH_IN_SECONDS


# ══════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════

SECRET_NAME = "sira/oauth/test-secret"

BASE_CREDS: dict = {
    "client_id":     "test_client_id",
    "client_secret": "test_client_secret",
    "token_url":     "https://auth.test.com/token",
    "audience":      "https://api.test.com",
}


def _secret_response(extra: dict | None = None, version_id: str = "v-001") -> dict:
    """Build a minimal Secrets Manager get_secret_value response."""
    payload = {**BASE_CREDS, **(extra or {})}
    return {
        "SecretString": json.dumps(payload),
        "VersionId":    version_id,
    }


def _client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "mocked error"}},
        "SecretsManager",
    )


@pytest.fixture
def mock_boto_client() -> Mock:
    return Mock()


@pytest.fixture
def secrets_client(mock_boto_client: Mock) -> SecretsManagerClient:
    with patch("boto3.client", return_value=mock_boto_client):
        client = SecretsManagerClient()
        client.secret_name = SECRET_NAME
        return client


# ══════════════════════════════════════════════════════════════════
# CRITICAL TESTS
# ══════════════════════════════════════════════════════════════════

def test_get_cached_jwt_returns_none_when_past_expiry(
    secrets_client: SecretsManagerClient,
    mock_boto_client: Mock,
) -> None:
    """
    Validates that an already-expired JWT is never served to callers.
    A past expiry timestamp must cause get_cached_jwt to return None,
    preventing expired tokens from reaching OAuth-protected APIs.
    """
    # Arrange — JWT expired 60 seconds ago
    expired_at = int(time.time()) - 60
    mock_boto_client.get_secret_value.return_value = _secret_response(
        extra={"cached_jwt": "expired.jwt.token", "cached_jwt_expires_at": expired_at}
    )

    # Act
    result = secrets_client.get_cached_jwt("AWSCURRENT")

    # Assert — expired token must never be returned
    assert result is None


def test_get_cached_jwt_returns_none_within_refresh_buffer(
    secrets_client: SecretsManagerClient,
    mock_boto_client: Mock,
) -> None:
    """
    Validates that a token expiring within the refresh buffer window is treated
    as expired and triggers re-acquisition before it actually expires in production.
    This is the core rotation trigger — an off-by-one here causes live API failures.
    """
    # Arrange — token expires exactly at the refresh boundary (e.g. 300s from now)
    near_expiry = int(time.time()) + TOKEN_REFRESH_IN_SECONDS - 1
    mock_boto_client.get_secret_value.return_value = _secret_response(
        extra={"cached_jwt": "near-expiry.jwt", "cached_jwt_expires_at": near_expiry}
    )

    # Act
    result = secrets_client.get_cached_jwt("AWSCURRENT")

    # Assert — token within buffer is treated as expired
    assert result is None


def test_store_jwt_preserves_original_credentials(
    secrets_client: SecretsManagerClient,
    mock_boto_client: Mock,
) -> None:
    """
    Validates that writing a new JWT to Secrets Manager does not overwrite
    existing credential fields such as client_id and client_secret.
    Data loss here would cause a permanent credential lockout with no recovery path.
    """
    # Arrange — existing secret has full credential set
    mock_boto_client.get_secret_value.return_value = _secret_response()
    future_expiry = int(time.time()) + 3600

    # Act
    secrets_client.store_jwt(
        token="new.jwt.token",
        expires_at=future_expiry,
        stage="AWSCURRENT",
    )

    # Assert — update_secret called with all original fields intact
    _, kwargs = mock_boto_client.update_secret.call_args
    stored: dict = json.loads(kwargs["SecretString"])
    assert stored["client_id"]              == "test_client_id"
    assert stored["client_secret"]          == "test_client_secret"
    assert stored["cached_jwt"]             == "new.jwt.token"
    assert stored["cached_jwt_expires_at"]  == future_expiry


def test_store_jwt_calls_update_secret_with_correct_arguments(
    secrets_client: SecretsManagerClient,
    mock_boto_client: Mock,
) -> None:
    """
    Validates that update_secret is called with the exact SecretId and
    SecretString arguments required by the AWS API.
    Incorrect arguments silently write to the wrong secret version in production.
    """
    # Arrange
    mock_boto_client.get_secret_value.return_value = _secret_response()
    future_expiry = int(time.time()) + 3600

    # Act
    secrets_client.store_jwt(
        token="correct.jwt.token",
        expires_at=future_expiry,
        stage="AWSCURRENT",
    )

    # Assert — exactly one call with correct SecretId
    mock_boto_client.update_secret.assert_called_once()
    _, kwargs = mock_boto_client.update_secret.call_args
    assert kwargs["SecretId"]     == SECRET_NAME
    assert "cached_jwt" in json.loads(kwargs["SecretString"])


def test_promote_pending_to_current_calls_correct_api_arguments(
    secrets_client: SecretsManagerClient,
    mock_boto_client: Mock,
) -> None:
    """
    Validates that promote_pending_to_current calls update_secret_version_stage
    with the exact SecretId, VersionStage, and MoveToVersionId arguments.
    A wrong version id here permanently promotes the wrong credentials to AWSCURRENT.
    """
    # Arrange
    version_id = "abc-version-xyz-001"

    # Act
    secrets_client.promote_pending_to_current(version_id)

    # Assert — must call with exactly these three arguments, nothing else
    mock_boto_client.update_secret_version_stage.assert_called_once_with(
        SecretId        = SECRET_NAME,
        VersionStage    = "AWSCURRENT",
        MoveToVersionId = version_id,
    )


def test_get_pending_credentials_returns_none_when_awspending_missing(
    secrets_client: SecretsManagerClient,
    mock_boto_client: Mock,
) -> None:
    """
    Validates that get_pending_credentials returns None gracefully when no
    AWSPENDING version exists in Secrets Manager rather than raising an exception.
    The CredentialRotator depends on this contract — any other return value breaks
    the rotation guard and causes an unhandled exception mid-rotation.
    """
    # Arrange — AWS raises ResourceNotFoundException for missing AWSPENDING
    mock_boto_client.get_secret_value.side_effect = _client_error(
        "ResourceNotFoundException"
    )

    # Act
    result = secrets_client.get_pending_credentials()

    # Assert — must return None, not raise
    assert result is None
    mock_boto_client.get_secret_value.assert_called_once_with(
        SecretId     = SECRET_NAME,
        VersionStage = "AWSPENDING",
    )