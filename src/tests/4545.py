def test_missing_source_field_raises_400(monkeypatch):
    patch_runtime(monkeypatch)
    
    bad_body = {
        "request": {
            "header": {"correlationid": "123", "timestamp": "ts", "quoteEntryTime": "qet", "entityName": "e", "status": "s"},
            # Missing "source" field
        }
    }
    
    response = lambda_handler(build_event(bad_body), MockContext())
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Missing mandatory 'source' object in request body" in body["awsError"]


def test_service_unavailable_error_returns_503(valid_request_body, monkeypatch):
    patch_runtime(monkeypatch)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.side_effect = ServiceUnavailableError("Unable to acquire SIRA token")
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        assert result["statusCode"] == 503
        body = json.loads(result["body"])
        assert "Service unavailable calling SIRA" in body["awsError"]

def test_internal_server_error_returns_400(valid_request_body, monkeypatch):
    patch_runtime(monkeypatch)
    
    # Trigger validation error path
    bad_body = dict(valid_request_body)
    bad_body["request"].pop("header")  # Remove required field
    
    response = lambda_handler(build_event(bad_body), MockContext())
    
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "awsError" in body