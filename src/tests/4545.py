def test_kafka_disabled_continues_successfully(valid_request_body, monkeypatch):
    """When Kafka is disabled (ENABLE_KAFKA=False), Lambda still processes request."""
    # Disable Kafka
    monkeypatch.setattr("sira_integration.function.ENABLE_KAFKA", False)
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    monkeypatch.setattr("sira_integration.function.SIRA_TIMEOUT_SECONDS", 10.0)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        mock_rotator.oauth.make_rtq_request.return_value = {"resultStatus": "CLEAR"}
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["siraResponseJson"]["resultStatus"] == "CLEAR"