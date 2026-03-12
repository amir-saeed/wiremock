def test_invalid_json_body_returns_400(monkeypatch):
    """Invalid JSON in body raises InternalServerError."""
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    
    event = {
        "httpMethod": "POST",
        "path": "/sira/rtq",
        "headers": {"Content-Type": "application/json", "X-Consumer-Id": "test"},
        "body": "{ invalid json }"  # ← Invalid JSON
    }
    
    result = lambda_handler(event, MockContext())
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "Invalid JSON body" in body["awsError"]