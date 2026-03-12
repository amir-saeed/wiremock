def test_missing_workflow_name_returns_400(monkeypatch):
    """Missing mandatory WorkflowName field raises InternalServerError."""
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    
    bad_body = {
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
            }
            # Missing WorkflowName
        }
    }
    
    event = build_event(bad_body)
    result = lambda_handler(event, MockContext())
    
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "Missing mandatory 'WorkflowName' in request body" in body["awsError"]

    def test_missing_source_message_id_returns_400(monkeypatch):
    """Missing mandatory sourceMessageId field raises InternalServerError."""
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    
    bad_body = {
        "request": {
            "header": {
                "correlationid": "123",
                "timestamp": "2024-01-01T00:00:00Z",
                "quoteEntryTime": "2024-01-01T00:00:00Z",
                "entityName": "Synectics",
                "status": "success"
            },
            "source": {
                # Missing sourceMessageId
                "sourceData": "data"
            },
            "WorkflowName": "test_workflow"
        }
    }
    
    event = build_event(bad_body)
    result = lambda_handler(event, MockContext())
    
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "Missing mandatory 'source.sourceMessageId' in request body" in body["awsError"]

    def test_synectics_non_json_response_returns_error(valid_request_body, monkeypatch):
    """When Synectics returns non-JSON, Lambda handles it gracefully."""
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    monkeypatch.setattr("sira_integration.function.SIRA_TIMEOUT_SECONDS", 10.0)
    monkeypatch.setattr("sira_integration.function.ENABLE_KAFKA", False)  # Simplify
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        
        # Synectics returns 200 but response.json() fails
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Internal Server Error - Not JSON"
        mock_response.json.side_effect = Exception("Invalid JSON")
        
        http_error = requests.exceptions.HTTPError("HTTP Error")
        http_error.response = mock_response
        
        mock_rotator.oauth.make_rtq_request.side_effect = http_error
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        # Returns upstream status with text fallback
        assert result["statusCode"] == 200
def test_unexpected_exception_returns_500(valid_request_body, monkeypatch):
    """Unexpected exceptions return 500 with generic error."""
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    monkeypatch.setattr("sira_integration.function.ENABLE_KAFKA", False)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        # Raise a totally unexpected error
        mock_get_rotator.side_effect = RuntimeError("Unexpected error")
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "AWS/Lambda unexpected error" in body["awsError"]