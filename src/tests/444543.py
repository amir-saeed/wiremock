import json
import os
from unittest.mock import MagicMock, patch
import requests


class MockContext:
    function_name = "mock_function"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:test"
    aws_request_id = "mock_request_id"
    
    def get_remaining_time_in_millis(self):
        return 3000


def test_synectics_http_error():
    """Tests lines 457-501: HTTP error from Synectics with JSON response"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        # Mock successful token
        mock_token = MagicMock()
        mock_token.access_token = "valid-token"
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = mock_token
        
        # Create HTTP error from Synectics
        http_error = requests.exceptions.HTTPError("Bad Request")
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "type": "validation_error",
            "title": "Invalid Request",
            "status": 400,
            "detail": "Missing required field"
        }
        http_error.response = mock_response
        mock_rotator.oauth.make_rtq_request.side_effect = http_error
        
        with patch('sira_integration.function.validate'), \
             patch('sira_integration.function.load_schema', return_value={}), \
             patch('sira_integration.function.get_rotator', return_value=mock_rotator), \
             patch('sira_integration.function.publish_to_kafka'):
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-456",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
                        },
                        "source": {
                            "sourceMessageId": "msg-456",
                            "sourceData": "test data"
                        },
                        "WorkflowName": "TestWorkflow"
                    }
                })
            }
            
            response = handler(event, MockContext())
            
            print(f"Status: {response['statusCode']}")
            assert response["statusCode"] == 400
            assert response["headers"]["X-Error-Source"] == "SYNECTICS"
            
            body = json.loads(response["body"])
            assert "synecticsError" in body
            print("✅ HTTP ERROR TEST PASSED - Covers lines 457-501")


if __name__ == "__main__":
    test_synectics_http_error()