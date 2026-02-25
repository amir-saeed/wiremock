def test_expired_l1_cache_falls_through_to_oauth(
    rotator, mock_secrets, mock_oauth, token_cache, fake_creds, fake_token
):
    """Test 9: Expired L1 token → cache.get() returns None → OAuth called."""
    expired = JWTToken(access_token="expired.token", expires_in=-1)
    token_cache.set(expired)

    # Confirm cache considers it invalid
    assert token_cache.get() is None

    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token

    result = rotator.get_valid_token()

    assert result.access_token == "valid.jwt.token"
    mock_oauth.acquire_token.assert_called_once()


def test_acquire_token_called_with_correct_credentials(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token
):
    """Test 10: OAuth is called with AWSCURRENT credentials, not pending ones."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token

    rotator.get_valid_token()

    mock_oauth.acquire_token.assert_called_once_with(fake_creds)


def test_promote_not_called_on_successful_awscurrent(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token
):
    """Test 11: Happy path — promote_pending_to_current must NEVER be called."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token

    rotator.get_valid_token()

    mock_secrets.promote_pending_to_current.assert_not_called()
    mock_secrets.get_pending_credentials.assert_not_called()


def test_store_jwt_always_uses_awscurrent_stage(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token
):
    """Test 12: store_jwt stage is always 'AWSCURRENT', even after rotation."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token

    rotator.get_valid_token()

    _, kwargs = mock_secrets.store_jwt.call_args
    assert kwargs["stage"] == "AWSCURRENT"


def test_l1_cache_populated_after_normal_oauth_flow(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token, token_cache
):
    """Test 13: After normal OAuth, L1 cache is populated for next call."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token

    rotator.get_valid_token()

    # Second call must hit L1 — OAuth not called again
    rotator.get_valid_token()

    assert mock_oauth.acquire_token.call_count == 1
    assert token_cache.get().access_token == "valid.jwt.token"


def test_aws_client_error_throttling_does_not_trigger_rotation(
    rotator, mock_secrets, mock_oauth, fake_creds
):
    """Test 14: AWS ThrottlingException bubbles up — rotation must NOT happen."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.side_effect = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "AcquireToken",
    )

    with pytest.raises(ClientError):
        rotator.get_valid_token()

    mock_secrets.get_pending_credentials.assert_not_called()
    mock_secrets.promote_pending_to_current.assert_not_called()


def test_rotation_uses_pending_credentials_not_current(
    rotator, mock_secrets, mock_oauth, fake_creds, pending_creds, fake_token
):
    """Test 15: During rotation, OAuth is called with AWSPENDING creds, not AWSCURRENT."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_secrets.get_pending_credentials.return_value = (pending_creds, "v2")
    mock_oauth.acquire_token.side_effect = [
        BadCredentialsError("Bad credentials: 401"),
        fake_token,
    ]

    rotator.get_valid_token()

    # First call → fake_creds (AWSCURRENT), second → pending_creds (AWSPENDING)
    assert mock_oauth.acquire_token.call_args_list == [
        call(fake_creds),
        call(pending_creds),
    ]


def test_store_jwt_expires_at_matches_token(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token
):
    """Test 16: expires_at stored in Secrets Manager matches token.expires_at_unix()."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token

    rotator.get_valid_token()

    _, kwargs = mock_secrets.store_jwt.call_args
    assert kwargs["token"]      == fake_token.access_token
    assert kwargs["expires_at"] == fake_token.expires_at_unix()
    assert kwargs["expires_at"] > 0