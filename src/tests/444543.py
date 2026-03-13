def test_invalid_json_body():
    """Tests lines 245-246: Invalid JSON body"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        # Event with INVALID JSON in body
        event = {
            "httpMethod": "POST",
            "path": "/v1/sira",
            "headers": {"X-Consumer-Id": "test"},
            "isBase64Encoded": False,
            "body": "invalid json {{{{"  # Malformed JSON
        }
        
        response = handler(event, MockContext())
        
        print(f"Status: {response['statusCode']}")
        body = json.loads(response['body'])
        print(f"Error: {body}")
        
        assert response["statusCode"] == 500
        assert "Invalid JSON" in body['awsError']
        print("✅ INVALID JSON TEST PASSED - Covers lines 245-246")
