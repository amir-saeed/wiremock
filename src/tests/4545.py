def test_token_acquisition_failure_returns_503(valid_request_body, monkeypatch):
    patch_runtime(monkeypatch)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        
        # Add debug: verify the exception is raised
        from sira_integration.models.exceptions import ServiceUnavailableError
        
        mock_rotator.get_valid_token.side_effect = ServiceUnavailableError(
            "Unable to acquire SIRA token"
        )
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        
        # Add print to see what's happening
        try:
            result = lambda_handler(event, MockContext())
            print(f"Status: {result['statusCode']}")
            print(f"Body: {result['body']}")
        except Exception as e:
            print(f"Exception raised: {type(e).__name__}: {e}")
            raise
        
        assert result["statusCode"] == 502