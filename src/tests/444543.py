def test_invalid_header_object():
    """Tests line 289: Invalid/missing header object in request body"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        with patch('sira_integration.function.validate'), \
             patch('sira_integration.function.load_schema', return_value={}):
            
            # Event with NO header object at all (or wrong type)
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        # MISSING header object entirely
                        "source": {
                            "sourceMessageId": "msg-890",
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
            assert "header" in body['awsError'].lower()
            print("✅ INVALID HEADER OBJECT TEST PASSED - Covers line 289")
