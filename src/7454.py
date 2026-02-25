@pytest.mark.parametrize("error_code", ["UnauthorizedException", "AccessDeniedException"])
def test_client_error_auth_codes_trigger_rotation(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token, error_code
):
    """Test: ClientError with auth error codes must rotate to AWSPENDING."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_secrets.get_pending_credentials.return_value = (fake_creds, "v2")
    mock_oauth.acquire_token.side_effect = [
        ClientError(
            {"Error": {"Code": error_code, "Message": "Auth failed"}},
            "AcquireToken",
        ),
        fake_token,
    ]

    result = rotator.get_valid_token()

    assert result.access_token == "valid.jwt.token"
    mock_secrets.promote_pending_to_current.assert_called_once_with("v2")