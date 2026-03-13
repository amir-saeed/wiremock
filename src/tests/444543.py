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


def test_kafka_publish_exception_after_success():
    """Lines 434-435: Kafka publish fails after successful SIRA call"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'true'}):
        
        mock_token = MagicMock()
        mock_token.access_token = "valid-token"
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = mock_token
        mock_rotator.oauth.make_rtq_request.return_value = {"quoteId": "Q-999"}
        
        with patch('sira_integration.function.validate'), \
             patch('sira_integration.function.load_schema', return_value={}), \
             patch('sira_integration.function.get_rotator', return_value=mock_rotator), \
             patch('sira_integration.function.publish_to_kafka') as mock_kafka:
            
            # First call succeeds, second call (response publish) fails
            mock_kafka.side_effect = [None, Exception("Kafka down")]
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-kafka",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
                        },
                        "source": {
                            "sourceMessageId": "msg-kafka",
                            "sourceData": "test data"
                        },
                        "WorkflowName": "TestWorkflow"
                    }
                })
            }
            
            response = handler(event, MockContext())
            
            assert response["statusCode"] == 200  # Still succeeds despite Kafka failure
            assert mock_kafka.call_count == 2
            print("✅ KAFKA EXCEPTION TEST PASSED - Covers lines 434-435")


def test_http_error_text_response():
    """Lines 457-501: HTTP error from Synectics with text (non-JSON) response"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        mock_token = MagicMock()
        mock_token.access_token = "valid-token"
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = mock_token
        
        # HTTP error with TEXT response (not JSON)
        http_error = requests.exceptions.HTTPError("Server Error")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Internal server error occurred"
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
                            "correlationid": "test-http",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
                        },
                        "source": {
                            "sourceMessageId": "msg-http",
                            "sourceData": "test data"
                        },
                        "WorkflowName": "TestWorkflow"
                    }
                })
            }
            
            response = handler(event, MockContext())
            
            assert response["statusCode"] == 500
            assert response["headers"]["X-Error-Source"] == "SYNECTICS"
            body = json.loads(response["body"])
            assert "synecticsErrorRaw" in body
            print("✅ HTTP TEXT ERROR TEST PASSED - Covers lines 457-501")


def test_unexpected_exception():
    """Lines 543-544: Unexpected exception during processing"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        with patch('sira_integration.function.validate') as mock_validate:
            # Cause unexpected RuntimeError
            mock_validate.side_effect = RuntimeError("Unexpected system failure")
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-runtime",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
                        },
                        "source": {
                            "sourceMessageId": "msg-runtime",
                            "sourceData": "test data"
                        },
                        "WorkflowName": "TestWorkflow"
                    }
                })
            }
            
            response = handler(event, MockContext())
            
            assert response["statusCode"] == 500
            assert response["headers"]["X-Error-Source"] == "AWS"
            body = json.loads(response["body"])
            assert "awsError" in body
            assert "unexpected" in body["awsError"].lower()
            print("✅ UNEXPECTED EXCEPTION TEST PASSED - Covers lines 543-544")


# NOTE: Lines 375-376 and 520-521 involve ServiceUnavailableError
# which has exception handler ordering issues. Skipping those.


if __name__ == "__main__":
    test_kafka_publish_exception_after_success()
    test_http_error_text_response()
    test_unexpected_exception()
    print("\n✅ ALL 3 TESTS PASSED")
