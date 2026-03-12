def test_token_acquisition_failure_returns_503(valid_request_body, monkeypatch):
    patch_runtime(monkeypatch)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        # Token acquisition fails
        mock_rotator.get_valid_token.side_effect = Exception("Token service down")
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        assert result["statusCode"] == 503
        assert "Service unavailable" in json.loads(result["body"])["awsError"]