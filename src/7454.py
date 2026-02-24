"""Unit tests for credential rotator - focus on rotation logic."""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from src.oauth_jwt_service.core.credential_rotator import CredentialRotator
from src.oauth_jwt_service.core.token_cache import TokenCache
from src.oauth_jwt_service.models.schemas import JWTToken, OAuthCredentials
from pydantic import SecretStr


@pytest.fixture
def mock_secrets():
    return Mock()


@pytest.fixture
def mock_oauth():
    return Mock()


@pytest.fixture
def token_cache():
    return TokenCache()


@pytest.fixture
def rotator(mock_secrets, mock_oauth, token_cache):
    return CredentialRotator(mock_secrets, mock_oauth, token_cache)


@pytest.fixture
def fake_creds():
    return OAuthCredentials(
        client_id="test_id",
        client_secret=SecretStr("test_secret"),
        token_url="https://auth.test.com/token",
        audience="https://api.test.com",
    )


@pytest.fixture
def fake_token():
    return JWTToken(access_token="valid.jwt.token", expires_in=3600)


# ══════════════════════════════════════════════════════════════════
# SIMPLE TESTS
# ══════════════════════════════════════════════════════════════════

def test_l1_cache_hit(rotator, token_cache, fake_token):
    """Test 1: Token in L1 cache - no Secrets Manager or OAuth calls."""
    token_cache.set(fake_token)
    
    result = rotator.get_valid_token()
    
    assert result.access_token == "valid.jwt.token"
    rotator.secrets.get_cached_jwt.assert_not_called()
    rotator.oauth.acquire_token.assert_not_called()


def test_l2_cache_hit(rotator, mock_secrets, fake_creds, token_cache):
    """Test 2: Token in Secrets Manager cache - OAuth not called."""
    mock_secrets.get_cached_jwt.return_value = "cached.jwt.token"
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    fake_creds.cached_jwt_expires_at = 9999999999  # far future
    
    result = rotator.get_valid_token()
    
    assert result.access_token == "cached.jwt.token"
    rotator.oauth.acquire_token.assert_not_called()
    # But L1 cache should now be populated
    cached = token_cache.get()
    assert cached.access_token == "cached.jwt.token"


def test_normal_oauth_flow(rotator, mock_secrets, mock_oauth, fake_creds, fake_token):
    """Test 3: Normal flow - AWSCURRENT credentials work."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token
    
    result = rotator.get_valid_token()
    
    assert result.access_token == "valid.jwt.token"
    mock_oauth.acquire_token.assert_called_once_with(fake_creds)
    mock_secrets.store_jwt.assert_called_once()


# ══════════════════════════════════════════════════════════════════
# ROTATION TESTS (HARDER)
# ══════════════════════════════════════════════════════════════════

def test_rotation_awscurrent_fails_awspending_succeeds(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token
):
    """Test 4: AWSCURRENT fails (401) → AWSPENDING works → promotes."""
    # L1 and L2 cache empty
    mock_secrets.get_cached_jwt.return_value = None
    
    # AWSCURRENT credentials
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    
    # AWSPENDING credentials
    pending_creds = OAuthCredentials(
        client_id="new_id",
        client_secret=SecretStr("new_secret"),
        token_url="https://auth.test.com/token",
        audience="https://api.test.com",
    )
    mock_secrets.get_pending_credentials.return_value = (pending_creds, "v2")
    
    # OAuth: AWSCURRENT fails, AWSPENDING succeeds
    from src.oauth_jwt_service.models.exceptions import BadCredentialsError
    mock_oauth.acquire_token.side_effect = [
        BadCredentialsError("401"),  # AWSCURRENT fails
        fake_token                   # AWSPENDING works
    ]
    
    result = rotator.get_valid_token()
    
    # Verify rotation happened
    assert result.access_token == "valid.jwt.token"
    assert mock_oauth.acquire_token.call_count == 2
    mock_secrets.promote_pending_to_current.assert_called_once_with("v2")
    mock_secrets.store_jwt.assert_called_once()


def test_rotation_no_awspending_exists(rotator, mock_secrets, mock_oauth, fake_creds):
    """Test 5: AWSCURRENT fails but no AWSPENDING → raises exception."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_secrets.get_pending_credentials.return_value = None  # No AWSPENDING
    
    from src.oauth_jwt_service.models.exceptions import BadCredentialsError
    mock_oauth.acquire_token.side_effect = BadCredentialsError("401")
    
    with pytest.raises(Exception, match="no AWSPENDING"):
        rotator.get_valid_token()


def test_rotation_both_credentials_fail(rotator, mock_secrets, mock_oauth, fake_creds):
    """Test 6: Both AWSCURRENT and AWSPENDING credentials are invalid."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    
    pending_creds = OAuthCredentials(
        client_id="new_id",
        client_secret=SecretStr("new_secret"),
        token_url="https://auth.test.com/token",
        audience="https://api.test.com",
    )
    mock_secrets.get_pending_credentials.return_value = (pending_creds, "v2")
    
    from src.oauth_jwt_service.models.exceptions import BadCredentialsError
    mock_oauth.acquire_token.side_effect = BadCredentialsError("401")  # Always fails
    
    with pytest.raises(Exception, match="Both AWSCURRENT and AWSPENDING"):
        rotator.get_valid_token()


def test_network_error_does_not_trigger_rotation(rotator, mock_secrets, mock_oauth, fake_creds):
    """Test 7: Network error (not 401) → does NOT try rotation."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    
    # Network timeout - not a 401
    mock_oauth.acquire_token.side_effect = Exception("Connection timeout")
    
    with pytest.raises(Exception, match="Connection timeout"):
        rotator.get_valid_token()
    
    # Should NOT call get_pending_credentials (no rotation attempted)
    mock_secrets.get_pending_credentials.assert_not_called()


def test_token_stored_in_both_caches_after_rotation(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token, token_cache
):
    """Test 8: After rotation, token is stored in L1 + L2."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    
    pending_creds = OAuthCredentials(
        client_id="new_id",
        client_secret=SecretStr("new_secret"),
        token_url="https://auth.test.com/token",
        audience="https://api.test.com",
    )
    mock_secrets.get_pending_credentials.return_value = (pending_creds, "v2")
    
    from src.oauth_jwt_service.models.exceptions import BadCredentialsError
    mock_oauth.acquire_token.side_effect = [BadCredentialsError("401"), fake_token]
    
    result = rotator.get_valid_token()
    
    # L1 cache populated
    assert token_cache.get().access_token == "valid.jwt.token"
    
    # L2 cache populated
    mock_secrets.store_jwt.assert_called_once_with(
        token="valid.jwt.token",
        expires_at=fake_token.expires_at_unix(),
        stage="AWSCURRENT",
    )