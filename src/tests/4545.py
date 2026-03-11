"""Critical unit tests for OAuthClient."""
import pytest
import requests
from unittest.mock import Mock, patch
from pydantic import ValidationError

from sira_integration.core.oauth_client import OAuthClient
from sira_integration.models.schemas import OAuthCredentials, JWTToken
from sira_integration.models.exceptions import BadCredentialsError, OAuthProviderError


@pytest.fixture
def oauth_credentials() -> OAuthCredentials:
    """Valid OAuth credentials for testing."""
    return OAuthCredentials(
        token_url="https://auth.example.com/oauth/token",
        client_id="test_client_id",
        client_secret="test_client_secret",
        audience="https://api.example.com",
    )


@pytest.fixture
def oauth_client() -> OAuthClient:
    """OAuthClient instance."""
    return OAuthClient()


@pytest.fixture
def mock_session():
    """Mock the module-level _session."""
    with patch("sira_integration.core.oauth_client._session") as mock:
        yield mock


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL TEST 1: Success Path
# ═══════════════════════════════════════════════════════════════════════════════
def test_acquire_token_success(
    oauth_client: OAuthClient,
    oauth_credentials: OAuthCredentials,
    mock_session: Mock,
) -> None:
    """
    CRITICAL 1 — Happy Path
    Valid credentials and 200 response must return JWTToken with correct fields.
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 3600,
    }
    mock_session.post.return_value = mock_response

    # Act
    token = oauth_client.acquire_token(oauth_credentials)

    # Assert
    assert isinstance(token, JWTToken)
    assert token.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    assert token.expires_in == 3600

    # Verify correct API call
    mock_session.post.assert_called_once_with(
        "https://auth.example.com/oauth/token",
        auth=("test_client_id", "test_client_secret"),
        data={
            "grant_type": "client_credentials",
            "audience": "https://api.example.com",
        },
        timeout=(5, 25),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL TEST 2: 401 Unauthorized
# ═══════════════════════════════════════════════════════════════════════════════
def test_acquire_token_raises_bad_credentials_on_401(
    oauth_client: OAuthClient,
    oauth_credentials: OAuthCredentials,
    mock_session: Mock,
) -> None:
    """
    CRITICAL 2 — Bad Credentials
    OAuth provider returns 401 must raise BadCredentialsError.
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 401
    mock_session.post.return_value = mock_response

    # Act & Assert
    with pytest.raises(BadCredentialsError, match="Bad credentials - OAuth provider returned 401"):
        oauth_client.acquire_token(oauth_credentials)


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL TEST 3: HTTP Errors (4xx/5xx except 401)
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("status_code", [403, 500, 502, 503, 504])
def test_acquire_token_raises_oauth_error_on_http_error(
    oauth_client: OAuthClient,
    oauth_credentials: OAuthCredentials,
    mock_session: Mock,
    status_code: int,
) -> None:
    """
    CRITICAL 3 — HTTP Errors
    Non-401 HTTP errors (403, 500, 503, etc.) must raise OAuthProviderError.
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )
    mock_session.post.return_value = mock_response

    # Act & Assert
    with pytest.raises(OAuthProviderError, match=f"OAuth provider HTTP error: {status_code}"):
        oauth_client.acquire_token(oauth_credentials)


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL TEST 4: Network Timeout
# ═══════════════════════════════════════════════════════════════════════════════
def test_acquire_token_raises_oauth_error_on_timeout(
    oauth_client: OAuthClient,
    oauth_credentials: OAuthCredentials,
    mock_session: Mock,
) -> None:
    """
    CRITICAL 4 — Timeout
    Network timeout must raise OAuthProviderError with timeout message.
    """
    # Arrange
    mock_session.post.side_effect = requests.exceptions.Timeout("Connection timed out")

    # Act & Assert
    with pytest.raises(OAuthProviderError, match="OAuth provider timeout"):
        oauth_client.acquire_token(oauth_credentials)


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL TEST 5: Connection Error
# ═══════════════════════════════════════════════════════════════════════════════
def test_acquire_token_raises_oauth_error_on_connection_error(
    oauth_client: OAuthClient,
    oauth_credentials: OAuthCredentials,
    mock_session: Mock,
) -> None:
    """
    CRITICAL 5 — Connection Failure
    Connection errors (DNS, refused, etc.) must raise OAuthProviderError.
    """
    # Arrange
    mock_session.post.side_effect = requests.exceptions.ConnectionError(
        "Failed to establish connection"
    )

    # Act & Assert
    with pytest.raises(OAuthProviderError, match="OAuth provider unreachable"):
        oauth_client.acquire_token(oauth_credentials)


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL TEST 6: Invalid Response Schema
# ═══════════════════════════════════════════════════════════════════════════════
def test_acquire_token_raises_oauth_error_on_invalid_response_schema(
    oauth_client: OAuthClient,
    oauth_credentials: OAuthCredentials,
    mock_session: Mock,
) -> None:
    """
    CRITICAL 6 — Malformed Response
    Valid 200 but invalid JWTToken schema must raise OAuthProviderError.
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "invalid_field": "missing required fields",
        # Missing: access_token, expires_in
    }
    mock_session.post.return_value = mock_response

    # Act & Assert
    with pytest.raises(OAuthProviderError, match="Invalid token response schema"):
        oauth_client.acquire_token(oauth_credentials)