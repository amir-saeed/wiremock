def test_synectics_http_error_returns_upstream_status(valid_request_body, monkeypatch):
    patch_runtime(monkeypatch)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        
        # Synectics returns 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = Exception("Not JSON")  # Force text fallback
        
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        
        mock_rotator.oauth.make_rtq_request.side_effect = http_error
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        # Lambda returns Synectics' status code
        assert result["statusCode"] == 500  # ← NOT 200
        assert result["headers"]["X-Error-Source"] == "SYNECTICS"
        body = json.loads(result["body"])
        assert "awsError" in body