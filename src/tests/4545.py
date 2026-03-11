"""
Critical unit tests for OAuthClient.acquire_token method.
Tests cover core functionality and error handling paths.
"""
import pytest
import requests
from unittest.mock import Mock, patch
from pydantic import ValidationError

from sira_integration.core.oauth_client import OAuthClient
from sira_integration.models.schemas import OAuthCredentials, JWTToken
from sira_integration.models.exceptions import BadCredentialsError, OAuthProviderError


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_credentials() -> OAuthCredentials:
    """Valid OAuth credentials for testing."""
    return OAuthCredentials(
        token_url="https://auth.example.com/oauth/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        audience="https://api.example.com",
    )


@pytest.fixture
def valid_token_response() -> dict:
    """Valid OAuth token response payload."""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


@pytest.fixture
def oauth_client() -> OAuthClient:
    """OAuthClient instance for testing."""
    return OAuthClient()


@pytest.fixture
def mock_session_post():
    """Mock the module-level _session.post method."""
    with patch("sira_integration.core.oauth_client._session.post") as mock:
        yield mock


# ── CRITICAL Test 1: Success Path ──────────────────────────────────────────

def test_acquire_token_success(
    oauth_client: OAuthClient,
    valid_credentials: OAuthCredentials,
    valid_token_response: dict,
    mock_session_post: Mock,
) -> None:
    """
    Test 1 - Happy Path: Valid credentials return a JWTToken.
    
    Validates that successful OAuth flow:
    - Returns JWTToken with correct fields
    - Posts to correct URL with correct auth and data
    - Uses proper timeout configuration
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = valid_token_response
    mock_session_post.return_value = mock_response
    
    # Act
    token = oauth_client.acquire_token(valid_credentials)
    
    # Assert - Token structure
    assert isinstance(token, JWTToken)
    assert token.access_token == valid_token_response["access_token"]
    assert token.expires_in == valid_token_response["expires_in"]
    
    # Assert - HTTP call made correctly
    mock_session_post.assert_called_once_with(
        "https://auth.example.com/oauth/token",
        auth=("test_client_id", "test_client_secret"),
        data={
            "grant_type": "client_credentials",
            "audience": "https://api.example.com",
        },
        timeout=(5, 25),
    )


# ── CRITICAL Test 2: 401 Bad Credentials ───────────────────────────────────

def test_acquire_token_raises_bad_credentials_on_401(
    oauth_client: OAuthClient,
    valid_credentials: OAuthCredentials,
    mock_session_post: Mock,
) -> None:
    """
    Test 2 - Authentication Failure: 401 raises BadCredentialsError.
    
    Validates that invalid client credentials are detected and reported
    with the correct exception type for upstream rotation logic.
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 401
    mock_session_post.return_value = mock_response
    
    # Act & Assert
    with pytest.raises(BadCredentialsError) as exc_info:
        oauth_client.acquire_token(valid_credentials)
    
    assert "Bad credentials - OAuth provider returned 401" in str(exc_info.value)


# ── CRITICAL Test 3: HTTP Errors (Non-401) ─────────────────────────────────

@pytest.mark.parametrize(
    "status_code",
    [403, 500, 502, 503, 504],
    ids=["forbidden", "internal_error", "bad_gateway", "unavailable", "timeout"],
)
def test_acquire_token_raises_oauth_error_on_http_error(
    oauth_client: OAuthClient,
    valid_credentials: OAuthCredentials,
    mock_session_post: Mock,
    status_code: int,
) -> None:
    """
    Test 3 - HTTP Errors: Non-401 HTTP errors raise OAuthProviderError.
    
    Validates that OAuth provider issues (rate limits, server errors,
    maintenance) are wrapped in OAuthProviderError for consistent handling.
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )
    mock_session_post.return_value = mock_response
    
    # Act & Assert
    with pytest.raises(OAuthProviderError) as exc_info:
        oauth_client.acquire_token(valid_credentials)
    
    assert "OAuth provider HTTP error" in str(exc_info.value)
    assert str(status_code) in str(exc_info.value)
    assert exc_info.value.__cause__ is not None  # Verify exception chaining


# ── CRITICAL Test 4: Network Timeout ───────────────────────────────────────

def test_acquire_token_raises_oauth_error_on_timeout(
    oauth_client: OAuthClient,
    valid_credentials: OAuthCredentials,
    mock_session_post: Mock,
) -> None:
    """
    Test 4 - Network Timeout: Timeout raises OAuthProviderError.
    
    Validates that slow OAuth provider responses are caught and wrapped
    with a clear error message for retry logic upstream.
    """
    # Arrange
    mock_session_post.side_effect = requests.exceptions.Timeout("Connection timeout")
    
    # Act & Assert
    with pytest.raises(OAuthProviderError) as exc_info:
        oauth_client.acquire_token(valid_credentials)
    
    assert "OAuth provider timeout" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None  # Verify exception chaining


# ── CRITICAL Test 5: Connection Error ──────────────────────────────────────

def test_acquire_token_raises_oauth_error_on_connection_error(
    oauth_client: OAuthClient,
    valid_credentials: OAuthCredentials,
    mock_session_post: Mock,
) -> None:
    """
    Test 5 - Connection Failure: Network errors raise OAuthProviderError.
    
    Validates that DNS failures, connection refused, and network
    unreachability are caught and reported consistently.
    """
    # Arrange
    mock_session_post.side_effect = requests.exceptions.ConnectionError(
        "Failed to establish connection"
    )
    
    # Act & Assert
    with pytest.raises(OAuthProviderError) as exc_info:
        oauth_client.acquire_token(valid_credentials)
    
    assert "OAuth provider unreachable" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None  # Verify exception chaining


# ── CRITICAL Test 6: Invalid Response Schema ───────────────────────────────

@pytest.mark.parametrize(
    "invalid_response",
    [
        {},  # Empty response
        {"access_token": "token"},  # Missing expires_in
        {"expires_in": 3600},  # Missing access_token
        {"access_token": 123, "expires_in": "invalid"},  # Wrong types
    ],
    ids=["empty", "missing_expires_in", "missing_access_token", "wrong_types"],
)
def test_acquire_token_raises_oauth_error_on_invalid_response_schema(
    oauth_client: OAuthClient,
    valid_credentials: OAuthCredentials,
    mock_session_post: Mock,
    invalid_response: dict,
) -> None:
    """
    Test 6 - Schema Validation: Invalid token response raises OAuthProviderError.
    
    Validates that malformed OAuth responses (missing fields, wrong types)
    are detected via Pydantic validation and wrapped appropriately.
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = invalid_response
    mock_session_post.return_value = mock_response
    
    # Act & Assert
    with pytest.raises(OAuthProviderError) as exc_info:
        oauth_client.acquire_token(valid_credentials)
    
    assert "Invalid token response schema" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ValidationError)


# ── Additional Validation Tests (Optional but Recommended) ─────────────────

def test_acquire_token_handles_credentials_without_audience(
    oauth_client: OAuthClient,
    valid_token_response: dict,
    mock_session_post: Mock,
) -> None:
    """
    Bonus Test: Credentials without audience exclude it from request data.
    
    Some OAuth providers don't require audience parameter - verify
    it's conditionally included only when present.
    """
    # Arrange
    credentials = OAuthCredentials(
        token_url="https://auth.example.com/oauth/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        audience=None,  # No audience
    )
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = valid_token_response
    mock_session_post.return_value = mock_response
    
    # Act
    oauth_client.acquire_token(credentials)
    
    # Assert - audience not in request data
    call_kwargs = mock_session_post.call_args.kwargs
    assert "audience" not in call_kwargs["data"]
    assert call_kwargs["data"]["grant_type"] == "client_credentials"