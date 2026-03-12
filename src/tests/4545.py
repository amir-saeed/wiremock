def test_synectics_http_error_publishes_failure_to_kafka(valid_request_body, monkeypatch):
    patch_runtime(monkeypatch)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        
        # Synectics returns 500 error
        mock_rotator.oauth.make_rtq_request.side_effect = requests.exceptions.HTTPError(
            response=MagicMock(status_code=500, text="Internal Server Error")
        )
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        # Lambda still returns 200 to API Gateway
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        # But Kafka gets the failure
        assert body["siraResponseJson"]["resultStatus"] == "CLEAR"  # Default on error