def test_missing_correlationid_returns_400(monkeypatch):
    """Missing correlationid in header raises error."""
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    
    bad_body = {
        "request": {
            "header": {
                # Missing correlationid
                "timestamp": "2024-01-01T00:00:00Z",
                "quoteEntryTime": "2024-01-01T00:00:00Z",
                "entityName": "Synectics",
                "status": "success"
            },
            "source": {"sourceMessageId": "123", "sourceData": "data"},
            "WorkflowName": "test"
        }
    }
    
    event = build_event(bad_body)
    result = lambda_handler(event, MockContext())
    
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "Missing mandatory header fields" in body["awsError"]