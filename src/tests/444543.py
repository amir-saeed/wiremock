
def test_kafka_publish_failure_in_service_unavailable():
    """Tests lines 520-521: Kafka publish fails when handling ServiceUnavailableError"""
    from sira_integration.function import handler
    from aws_lambda_powertools.event_handler.exceptions import ServiceUnavailableError
    
    with patch.dict(os.environ, {
        'SYNECTICS_RTQ_URL': 'http://test.com',
        'ENABLE_KAFKA': 'true',
        'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092'
    }):
        
        # Mock token failure that raises ServiceUnavailableError
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.side_effect = ServiceUnavailableError("Token service down")
        
        # Mock Kafka to fail on the SECOND call (failure response publish)
        mock_publish = MagicMock()
        mock_publish.side_effect = [None, Exception("Kafka broker down")]  # First succeeds, second fails
        
        with patch('sira_integration.function.validate'), \
             patch('sira_integration.function.load_schema', return_value={}), \
             patch('sira_integration.function.get_rotator', return_value=mock_rotator), \
             patch('sira_integration.function.publish_to_kafka', mock_publish), \
             patch('sira_integration.function.build_kafka_request_payload', return_value={}), \
             patch('sira_integration.function.build_kafka_response_failure_payload', return_value={}):
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-789",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
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
            assert response["statusCode"] == 502  # Still returns 502 despite Kafka failure
            assert mock_publish.call_count == 2  # Called twice
            print("✅ KAFKA FAILURE TEST PASSED - Covers lines 520-521")