def test_kafka_request_publish_failure_continues(valid_request_body, monkeypatch):
    patch_runtime(monkeypatch)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator, \
         patch("sira_integration.function.publish_to_kafka") as mock_publish:
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        mock_rotator.oauth.make_rtq_request.return_value = {"resultStatus": "CLEAR"}
        mock_get_rotator.return_value = mock_rotator
        
        # First call (request publish) fails, second (response publish) succeeds
        mock_publish.side_effect = [Exception("Kafka down"), None]
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        # Lambda continues despite Kafka failure
        assert result["statusCode"] == 200
        # Response publish still attempted
        assert mock_publish.call_count == 2