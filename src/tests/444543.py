def test_missing_required_header_fields():
    """Tests lines 282, 289: Missing mandatory header fields validation"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        with patch('sira_integration.function.validate'), \
             patch('sira_integration.function.load_schema', return_value={}):
            
            # Event with MISSING header fields (only correlationid present)
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-789"
                            # MISSING: timestamp, quoteEntryTime, entityName, status
                        },
                        "source": {
                            "sourceMessageId": "msg-789",
                            "sourceData": "test data"
                        },
                        "WorkflowName": "TestWorkflow"
                    }
                })
            }
            
            response = handler(event, MockContext())
            
            print(f"Status: {response['statusCode']}")
            body = json.loads(response['body'])
            print(f"Error: {body}")
            
            assert response["statusCode"] == 500
            assert "Missing mandatory header fields" in body['awsError']
            print("✅ MISSING HEADERS TEST PASSED - Covers lines 282, 289")
