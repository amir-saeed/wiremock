"""
6 Critical Independent Unit Tests for Lambda Handler
Each test is standalone and can run independently
"""

import json
import pytest
from unittest.mock import Mock, patch
import requests


# ============================================================================
# TEST 1: TOKEN ACQUISITION FAILURE (Lines 375-376) - MOST CRITICAL
# ============================================================================
@patch.dict('os.environ', {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'})
@patch('function.validate')
@patch('function.get_rotator')
def test_critical_token_acquisition_failure(mock_get_rotator, mock_validate):
    """
    CRITICAL: Tests ServiceUnavailableError when token service is down
    Lines Covered: 375-376
    
    This is the most critical test as it validates authentication failure handling.
    Without proper token acquisition, no SIRA calls can be made.
    """
    from function import handler
    
    # Mock token service failure
    mock_rotator = Mock()
    mock_rotator.get_valid_token.side_effect = Exception("Token service unavailable")
    mock_get_rotator.return_value = mock_rotator
    
    # Valid request body
    event = {
        "httpMethod": "POST",
        "path": "/test",
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
    
    # Assertions
    assert response["statusCode"] == 502, "Should return 502 when token acquisition fails"
    assert response["headers"]["X-Error-Source"] == "AWS", "Error source should be AWS"
    assert "awsError" in json.loads(response["body"]), "Should include AWS error in response"
    
    # Verify token acquisition was attempted
    mock_rotator.get_valid_token.assert_called_once()
    
    print("✓ TEST 1 PASSED: Token acquisition failure handled correctly")


# ============================================================================
# TEST 2: SYNECTICS HTTP ERROR WITH JSON RESPONSE (Lines 457-501) - CRITICAL
# ============================================================================
@patch.dict('os.environ', {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'})
@patch('function.validate')
@patch('function.get_rotator')
def test_critical_synectics_http_error_json_response(mock_get_rotator, mock_validate):
    """
    CRITICAL: Tests HTTPError handling with JSON error from Synectics
    Lines Covered: 441, 457-501
    
    Critical for handling downstream API failures with structured error responses.
    Ensures error details are properly extracted and propagated.
    """
    from function import handler
    
    # Mock successful token but failed SIRA call
    mock_token = Mock()
    mock_token.access_token = "valid-token-123"
    mock_rotator = Mock()
    mock_rotator.get_valid_token.return_value = mock_token
    
    # Create HTTP error with JSON response
    http_error = requests.exceptions.HTTPError("Bad Request")
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "type": "validation_error",
        "title": "Invalid Request",
        "status": 400,
        "detail": "Missing required field: sourceData",
        "traceId": "trace-abc-123"
    }
    mock_response.text = json.dumps(mock_response.json.return_value)
    http_error.response = mock_response
    
    mock_rotator.oauth.make_rtq_request.side_effect = http_error
    mock_get_rotator.return_value = mock_rotator
    
    event = {
        "httpMethod": "POST",
        "path": "/test",
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
    
    response = handler(event, {})
    
    # Assertions
    assert response["statusCode"] == 400, "Should propagate Synectics status code"
    assert response["headers"]["X-Error-Source"] == "SYNECTICS", "Error source should be SYNECTICS"
    
    response_body = json.loads(response["body"])
    assert "synecticsError" in response_body, "Should include synecticsError object"
    assert response_body["synecticsError"]["title"] == "Invalid Request", "Should preserve error details"
    assert response_body["synecticsError"]["traceId"] == "trace-abc-123", "Should include traceId"
    
    print("✓ TEST 2 PASSED: Synectics HTTP error with JSON handled correctly")


# ============================================================================
# TEST 3: REQUEST VALIDATION FAILURES (Lines 241, 245-246, 249, 300, 308) - CRITICAL
# ============================================================================
@patch.dict('os.environ', {'SYNECTICS_RTQ_URL': 'http://test.com'})
def test_critical_request_validation_failures():
    """
    CRITICAL: Tests multiple request validation failure scenarios
    Lines Covered: 241, 245-246, 249, 300, 308, 314, 320
    
    Critical for security and data integrity. Prevents malformed requests
    from reaching downstream services.
    """
    from function import handler
    
    # Test 1: Invalid JSON body (Lines 245-246)
    event_invalid_json = {
        "httpMethod": "POST",
        "path": "/test",
        "headers": {},
        "body": "invalid json {"
    }
    
    response = handler(event_invalid_json, {})
    assert response["statusCode"] == 500, "Should return 500 for invalid JSON"
    assert "Invalid JSON" in response["body"], "Should indicate JSON parsing error"
    
    # Test 2: Body not a dict (Line 249)
    event_array_body = {
        "httpMethod": "POST",
        "path": "/test",
        "headers": {},
        "body": json.dumps(["array", "not", "dict"])
    }
    
    response = handler(event_array_body, {})
    assert response["statusCode"] == 500, "Should return 500 for non-dict body"
    assert "must be a JSON object" in response["body"], "Should indicate type error"
    
    # Test 3: Missing source object (Line 300)
    with patch('function.validate'):
        event_missing_source = {
            "httpMethod": "POST",
            "path": "/test",
            "headers": {},
            "body": json.dumps({
                "request": {
                    "header": {
                        "correlationid": "test",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "quoteEntryTime": "2024-01-01T00:00:00Z",
                        "entityName": "Test",
                        "status": "success"
                    },
                    "WorkflowName": "TestWorkflow"
                    # Missing source
                }
            })
        }
        
        response = handler(event_missing_source, {})
        assert response["statusCode"] == 500, "Should return 500 for missing source"
        assert "Missing mandatory 'source'" in response["body"], "Should indicate missing source"
    
    # Test 4: Missing WorkflowName (Line 308)
    with patch('function.validate'):
        event_missing_workflow = {
            "httpMethod": "POST",
            "path": "/test",
            "headers": {},
            "body": json.dumps({
                "request": {
                    "header": {
                        "correlationid": "test",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "quoteEntryTime": "2024-01-01T00:00:00Z",
                        "entityName": "Test",
                        "status": "success"
                    },
                    "source": {
                        "sourceMessageId": "msg-123",
                        "sourceData": "data"
                    }
                    # Missing WorkflowName
                }
            })
        }
        
        response = handler(event_missing_workflow, {})
        assert response["statusCode"] == 500, "Should return 500 for missing WorkflowName"
        assert "Missing mandatory 'WorkflowName'" in response["body"]
    
    print("✓ TEST 3 PASSED: All request validation failures handled correctly")


# ============================================================================
# TEST 4: KAFKA PUBLISH FAILURE AFTER SUCCESSFUL SIRA CALL (Lines 405-408) - CRITICAL
# ============================================================================
@patch.dict('os.environ', {
    'SYNECTICS_RTQ_URL': 'http://test.com',
    'ENABLE_KAFKA': 'true',
    'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092'
})
@patch('function.validate')
@patch('function.get_rotator')
@patch('function.publish_to_kafka')
def test_critical_kafka_failure_after_successful_sira_call(mock_publish, mock_get_rotator, mock_validate):
    """
    CRITICAL: Tests that Kafka publish failures don't break successful SIRA calls
    Lines Covered: 405-408, 434-435
    
    Critical for system resilience. Ensures main business flow succeeds even if
    Kafka logging fails. This is a "fail-safe" design pattern.
    """
    from function import handler
    
    # Mock successful token and SIRA call
    mock_token = Mock()
    mock_token.access_token = "valid-token-xyz"
    mock_rotator = Mock()
    mock_rotator.get_valid_token.return_value = mock_token
    mock_rotator.oauth.make_rtq_request.return_value = {
        "quoteId": "Q-12345",
        "status": "approved",
        "amount": 50000
    }
    mock_get_rotator.return_value = mock_rotator
    
    # First call (request publish) succeeds, second call (response publish) fails
    mock_publish.side_effect = [None, Exception("Kafka broker unavailable")]
    
    event = {
        "httpMethod": "POST",
        "path": "/test",
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
    
    response = handler(event, {})
    
    # Assertions - CRITICAL: Should still return 200
    assert response["statusCode"] == 200, "Should return 200 despite Kafka failure"
    assert "siraResponseJson" in json.loads(response["body"]), "Should include SIRA response"
    
    response_body = json.loads(response["body"])
    assert response_body["siraResponseJson"]["quoteId"] == "Q-12345", "Should have correct quote data"
    
    # Verify Kafka publish was attempted twice
    assert mock_publish.call_count == 2, "Should attempt to publish request and response to Kafka"
    
    print("✓ TEST 4 PASSED: Main flow succeeds despite Kafka failure (resilience pattern)")


# ============================================================================
# TEST 5: UNEXPECTED EXCEPTION HANDLING (Lines 543-544) - CRITICAL
# ============================================================================
@patch.dict('os.environ', {'SYNECTICS_RTQ_URL': 'http://test.com'})
@patch('function.validate')
def test_critical_unexpected_exception_handling(mock_validate):
    """
    CRITICAL: Tests catch-all exception handler for unexpected system errors
    Lines Covered: 543-544
    
    Critical for system stability. Ensures any unexpected error is caught
    and returns proper error response instead of crashing.
    """
    from function import handler
    
    # Simulate unexpected runtime error
    mock_validate.side_effect = RuntimeError("Unexpected system error: memory allocation failed")
    
    event = {
        "httpMethod": "POST",
        "path": "/test",
        "headers": {"X-Consumer-Id": "test"},
        "body": json.dumps({
            "request": {
                "header": {
                    "correlationid": "test-999",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "quoteEntryTime": "2024-01-01T00:00:00Z",
                    "entityName": "TestEntity",
                    "status": "success"
                },
                "source": {
                    "sourceMessageId": "msg-999",
                    "sourceData": "test data"
                },
                "WorkflowName": "TestWorkflow"
            }
        })
    }
    
    response = handler(event, {})
    
    # Assertions
    assert response["statusCode"] == 500, "Should return 500 for unexpected errors"
    assert response["headers"]["X-Error-Source"] == "AWS", "Error source should be AWS"
    
    response_body = json.loads(response["body"])
    assert "awsError" in response_body, "Should include AWS error"
    assert "unexpected error" in response_body["awsError"].lower(), "Should indicate unexpected error"
    assert "memory allocation" in response_body["awsError"].lower(), "Should include original error message"
    
    print("✓ TEST 5 PASSED: Unexpected exceptions caught and handled gracefully")


# ============================================================================
# TEST 6: SERVICE UNAVAILABLE WITH KAFKA FAILURE (Lines 520-521) - CRITICAL
# ============================================================================
@patch.dict('os.environ', {
    'SYNECTICS_RTQ_URL': 'http://test.com',
    'ENABLE_KAFKA': 'true',
    'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092'
})
@patch('function.validate')
@patch('function.get_rotator')
@patch('function.publish_to_kafka')
def test_critical_service_unavailable_with_kafka_failure(mock_publish, mock_get_rotator, mock_validate):
    """
    CRITICAL: Tests ServiceUnavailableError path when Kafka also fails
    Lines Covered: 520-521
    
    Critical for cascading failure scenarios. Tests that even if both
    token service AND Kafka fail, the system handles it gracefully.
    """
    from function import handler
    
    # Mock token service failure
    mock_rotator = Mock()
    mock_rotator.get_valid_token.side_effect = Exception("Token rotation service down")
    mock_get_rotator.return_value = mock_rotator
    
    # Request publish succeeds, but failure publish also fails
    mock_publish.side_effect = [None, Exception("Kafka broker connection timeout")]
    
    event = {
        "httpMethod": "POST",
        "path": "/test",
        "headers": {"X-Consumer-Id": "test"},
        "isBase64Encoded": False,
        "body": json.dumps({
            "request": {
                "header": {
                    "correlationid": "test-000",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "quoteEntryTime": "2024-01-01T00:00:00Z",
                    "entityName": "TestEntity",
                    "status": "success"
                },
                "source": {
                    "sourceMessageId": "msg-000",
                    "sourceData": "test data"
                },
                "WorkflowName": "TestWorkflow"
            }
        })
    }
    
    response = handler(event, {})
    
    # Assertions
    assert response["statusCode"] == 502, "Should return 502 for service unavailable"
    assert response["headers"]["X-Error-Source"] == "AWS", "Error source should be AWS"
    
    response_body = json.loads(response["body"])
    assert "awsError" in response_body, "Should include AWS error"
    assert "failure before receiving" in response_body["awsError"].lower(), "Should indicate pre-SIRA failure"
    
    # Verify both publishes were attempted (request + failure response)
    assert mock_publish.call_count == 2, "Should attempt both Kafka publishes despite failures"
    
    print("✓ TEST 6 PASSED: Cascading failures (token + Kafka) handled gracefully")


# ============================================================================
# RUN ALL CRITICAL TESTS
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print("RUNNING 6 CRITICAL INDEPENDENT UNIT TESTS")
    print("="*80 + "\n")
    
    test_critical_token_acquisition_failure()
    test_critical_synectics_http_error_json_response()
    test_critical_request_validation_failures()
    test_critical_kafka_failure_after_successful_sira_call()
    test_critical_unexpected_exception_handling()
    test_critical_service_unavailable_with_kafka_failure()
    
    print("\n" + "="*80)
    print("✅ ALL 6 CRITICAL TESTS PASSED")
    print("="*80 + "\n")