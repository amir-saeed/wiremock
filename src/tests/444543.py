def test_missing_source_data():
    """Tests line 320: Missing/invalid sourceData"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        with patch('sira_integration.function.validate'), \
             patch('sira_integration.function.load_schema', return_value={}):
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-111",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
                        },
                        "source": {
                            "sourceMessageId": "msg-111",
                            "sourceData": ""  # EMPTY string - invalid
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
            assert "sourceData" in body['awsError']
            print("✅ MISSING SOURCE DATA TEST PASSED - Covers line 320")
