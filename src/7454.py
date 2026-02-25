def test_client_error_non_auth_code_bubbles_up(
    rotator, mock_secrets, mock_oauth, fake_creds
):
    """Test: ClientError with non-auth code (e.g. InternalServerError) 
    must re-raise — NOT rotate."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "AWS blew up"}},
        "AcquireToken",
    )

    with pytest.raises(ClientError) as exc_info:
        rotator.get_valid_token()

    assert exc_info.value.response["Error"]["Code"] == "InternalServerError"
    mock_secrets.get_pending_credentials.assert_not_called()
    mock_secrets.promote_pending_to_current.assert_not_called()