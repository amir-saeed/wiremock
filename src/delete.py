"""Unit tests for OAuthClient."""

import pytest
import requests
from unittest.mock import Mock, patch
from requests import HTTPError

from src.oauth_jwt_service.core.oauth_client import OAuthClient
from src.oauth_jwt_service.models.schemas import OAuthCredentials, JWTToken


@pytest.fixture
def credentials() -> OAuthCredentials:
    return OAuthCredentials(
        client_id="test_client_id",
        client_secret="test_client_secret",
        token_url="https://auth.example.com/oauth/token",
        audience="https://api.example.com",
    )


@pytest.fixture
def client() -> OAuthClient:
    return OAuthClient()


@pytest.fixture
def valid_token_response() -> dict:
    return {
        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.signature",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


def mock_response(status_code: int, json_data: dict = None) -> Mock:
    """Helper to create mock requests response."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    if status_code >= 400:
        response.raise_for_status.side_effect = HTTPError(
            response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


class TestOAuthClientAcquireToken:

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_success(self, mock_post, client, credentials, valid_token_response):
        """Happy path - returns JWTToken on 200."""
        mock_post.return_value = mock_response(200, valid_token_response)

        token = client.acquire_token(credentials)

        assert isinstance(token, JWTToken)
        assert token.access_token == valid_token_response["access_token"]
        assert token.expires_in == 3600

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_uses_basic_auth(self, mock_post, client, credentials, valid_token_response):
        """Ensure client_id/secret sent as Basic Auth, NOT in body."""
        mock_post.return_value = mock_response(200, valid_token_response)

        client.acquire_token(credentials)

        _, kwargs = mock_post.call_args
        assert kwargs["auth"] == (
            credentials.client_id,
            credentials.client_secret.get_secret_value(),
        )

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_sends_audience_in_body(self, mock_post, client, credentials, valid_token_response):
        """Audience must be in request body, not scope."""
        mock_post.return_value = mock_response(200, valid_token_response)

        client.acquire_token(credentials)

        _, kwargs = mock_post.call_args
        assert kwargs["data"]["audience"] == credentials.audience
        assert kwargs["data"]["grant_type"] == "client_credentials"
        assert "scope" not in kwargs["data"]

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_sends_correct_content_type(self, mock_post, client, credentials, valid_token_response):
        """Content-Type must be application/x-www-form-urlencoded."""
        mock_post.return_value = mock_response(200, valid_token_response)

        client.acquire_token(credentials)

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_timeout_set(self, mock_post, client, credentials, valid_token_response):
        """Timeout must be set to avoid hanging Lambda."""
        mock_post.return_value = mock_response(200, valid_token_response)

        client.acquire_token(credentials)

        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 30

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_raises_on_401(self, mock_post, client, credentials):
        """401 must raise bad credentials exception."""
        mock_post.return_value = mock_response(401)

        with pytest.raises(Exception, match="Bad credentials"):
            client.acquire_token(credentials)

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_raises_on_403(self, mock_post, client, credentials):
        """403 must raise HTTP error."""
        mock_post.return_value = mock_response(403)

        with pytest.raises(HTTPError):
            client.acquire_token(credentials)

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_raises_on_500(self, mock_post, client, credentials):
        """Server error must raise HTTP error."""
        mock_post.return_value = mock_response(500)

        with pytest.raises(HTTPError):
            client.acquire_token(credentials)

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_raises_on_connection_error(self, mock_post, client, credentials):
        """Network failure must propagate."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network down")

        with pytest.raises(requests.exceptions.ConnectionError):
            client.acquire_token(credentials)

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_raises_on_timeout(self, mock_post, client, credentials):
        """Timeout must propagate."""
        mock_post.side_effect = requests.exceptions.Timeout("Timed out")

        with pytest.raises(requests.exceptions.Timeout):
            client.acquire_token(credentials)

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_posts_to_correct_url(self, mock_post, client, credentials, valid_token_response):
        """Must POST to the token URL from credentials."""
        mock_post.return_value = mock_response(200, valid_token_response)

        client.acquire_token(credentials)

        args, _ = mock_post.call_args
        assert args[0] == credentials.token_url

    @patch("src.oauth_jwt_service.core.oauth_client.requests.post")
    def test_acquire_token_secret_not_exposed_in_body(self, mock_post, client, credentials, valid_token_response):
        """client_secret must NEVER appear in request body."""
        mock_post.return_value = mock_response(200, valid_token_response)

        client.acquire_token(credentials)

        _, kwargs = mock_post.call_args
        body = kwargs.get("data", {})
        assert "client_secret" not in body
        assert "client_id" not in body