  with patch('function.validate'), \
             patch('function.load_schema', return_value={}), \
             patch('function.get_rotator', return_value=mock_rotator), \
             patch('function.publish_to_kafka'), \
             patch('function.build_kafka_request_payload', return_value={}), \
             patch('function.build_kafka_response_failure_payload', return_value={}):
            
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
            assert response["statusCode"] == 502
            print("✅ PASSED")
