# Mock SUCCESS - no exceptions
        mock_token = MagicMock()
        mock_token.access_token = "valid-token"
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = mock_token  # Returns token, doesn't raise
        mock_rotator.oauth.make_rtq_request.return_value = {"quoteId": "Q-123", "status": "approved"}
        
        with patch('function.validate'), \
             patch('function.load_schema', return_value={}), \
             patch('function.get_rotator', return_value=mock_rotator), \
             patch('function.publish_to_kafka'):
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-123",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
                        },
                        "source": {
                            "sourceMessageId": "msg-123",
                            "sourceData": "test data"
                        },
                        "WorkflowName": "TestWorkflow"
                    }
                })
            }
            
            response = handler(event, {})
            
            print(f"Status: {response['statusCode']}")
            assert response["statusCode"] == 200
            print("✅ SUCCESS TEST PASSED")