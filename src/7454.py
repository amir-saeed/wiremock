def test_bad_credentials_error_is_caught_by_client_error_block(
    rotator, mock_secrets, mock_oauth, fake_creds, pending_creds, fake_token
):
    """Test 19: BadCredentialsError is a ClientError subclass — confirm it is
    caught by the except ClientError block and triggers rotation correctly."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_secrets.get_pending_credentials.return_value = (pending_creds, "v2")

    # BadCredentialsError raised — must route through ClientError block
    mock_oauth.acquire_token.side_effect = [
        BadCredentialsError(
            {"Error": {"Code": "UnauthorizedException", "Message": "Bad credentials"}},
            "AcquireToken",
        ),
        fake_token,
    ]

    result = rotator.get_valid_token()

    assert result.access_token == "valid.jwt.token"
    mock_secrets.promote_pending_to_current.assert_called_once_with("v2")
    assert mock_oauth.acquire_token.call_count == 2


def test_promote_pending_fails_mid_rotation_raises_and_does_not_store(
    rotator, mock_secrets, mock_oauth, fake_creds, pending_creds, fake_token
):
    """Test 20: OAuth succeeds with AWSPENDING but promote_pending_to_current
    throws — token must NOT be stored in L1 or L2 (no partial state)."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_secrets.get_pending_credentials.return_value = (pending_creds, "v2")
    mock_secrets.promote_pending_to_current.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Version not found"}},
        "UpdateSecretVersionStage",
    )
    mock_oauth.acquire_token.side_effect = [
        BadCredentialsError(
            {"Error": {"Code": "UnauthorizedException", "Message": "Bad credentials"}},
            "AcquireToken",
        ),
        fake_token,
    ]

    with pytest.raises(ClientError) as exc_info:
        rotator.get_valid_token()

    assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"

    # No partial state — nothing stored
    mock_secrets.store_jwt.assert_not_called()
    assert rotator.cache.get() is None


def test_store_jwt_raises_after_successful_oauth_token_in_l1_not_l2(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token, token_cache
):
    """Test 21: OAuth succeeds, L1 cache is set, but store_jwt (L2) throws —
    token lives in L1 only. Next cold start will re-acquire from OAuth."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token
    mock_secrets.store_jwt.side_effect = ClientError(
        {"Error": {"Code": "InternalServiceError", "Message": "SM unavailable"}},
        "PutSecretValue",
    )

    with pytest.raises(ClientError):
        rotator.get_valid_token()

    # L1 was set before store_jwt was called — token is in memory
    assert token_cache.get().access_token == "valid.jwt.token"

    # L2 failed — store_jwt was attempted exactly once
    mock_secrets.store_jwt.assert_called_once()


def test_concurrent_cache_read_returns_same_token(
    rotator, mock_secrets, mock_oauth, fake_creds, fake_token, token_cache
):
    """Test 22: Simulate two sequential calls — second call must return the
    same token from L1 without calling OAuth or Secrets Manager again."""
    mock_secrets.get_cached_jwt.return_value = None
    mock_secrets.get_credentials.return_value = (fake_creds, "v1")
    mock_oauth.acquire_token.return_value = fake_token

    first  = rotator.get_valid_token()
    second = rotator.get_valid_token()

    assert first.access_token  == second.access_token == "valid.jwt.token"
    assert mock_oauth.acquire_token.call_count          == 1   # OAuth hit once only
    assert mock_secrets.get_cached_jwt.call_count       == 1   # SM hit once only
    assert mock_secrets.store_jwt.call_count            == 1   # stored once only


