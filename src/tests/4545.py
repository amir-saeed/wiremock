def test_base64_encoded_body_is_decoded(monkeypatch):
    """When body is base64 encoded (isBase64Encoded=true), decode it."""
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    monkeypatch.setattr("sira_integration.function.SIRA_TIMEOUT_SECONDS", 10.0)
    monkeypatch.setattr("sira_integration.function.ENABLE_KAFKA", False)
    
    valid_body = {
        "request": {
            "header": {
                "correlationid": "123",
                "timestamp": "2024-01-01T00:00:00Z",
                "quoteEntryTime": "2024-01-01T00:00:00Z",
                "entityName": "Synectics",
                "status": "success"
            },
            "source": {
                "sourceMessageId": "msg123",
                "sourceData": "data"
            },
            "WorkflowName": "test"
        }
    }
    
    # Base64 encode the body
    import base64
    encoded_body = base64.b64encode(json.dumps(valid_body).encode("utf-8")).decode("utf-8")
    
    event = {
        "httpMethod": "POST",
        "path": "/sira/rtq",
        "headers": {"Content-Type": "application/json", "X-Consumer-Id": "test"},
        "body": encoded_body,
        "isBase64Encoded": True  # ← This triggers line 236
    }
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        mock_rotator.oauth.make_rtq_request.return_value = {"resultStatus": "CLEAR"}
        mock_get_rotator.return_value = mock_rotator
        
        result = lambda_handler(event, MockContext())
        assert result["statusCode"] == 200