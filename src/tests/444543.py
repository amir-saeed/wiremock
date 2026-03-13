"""
ULTIMATE SIMPLE TEST - Just copy and run this!
Includes ALL required patches to avoid 400/500 errors
"""

import json
import os
from unittest.mock import MagicMock, patch
from contextlib import ExitStack


def test_token_failure_FINAL():
    """
    ✅ This works - returns 502 for token failure
    All patches included to avoid 400/500 errors
    """
    from function import handler
    
    # Setup environment
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        # Create mock that fails at token acquisition
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.side_effect = Exception("Token service unavailable")
        
        # Apply ALL patches (this is the key!)
        with ExitStack() as stack:
            # Patch 1: Skip schema validation
            stack.enter_context(patch('function.validate'))
            
            # Patch 2: Skip schema file loading
            stack.enter_context(patch('function.load_schema', return_value={}))
            
            # Patch 3: Use our mock rotator
            stack.enter_context(patch('function.get_rotator', return_value=mock_rotator))
            
            # Patch 4: Skip Kafka (optional but cleaner)
            stack.enter_context(patch('function.publish_to_kafka'))
            
            # Create request event
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test", "Content-Type": "application/json"},
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
            
            # Call handler
            response = handler(event, {})
            
            # Print results
            print(f"\n{'='*70}")
            print(f"Status Code: {response['statusCode']}")
            print(f"Headers: {response['headers']}")
            print(f"Body: {json.dumps(json.loads(response['body']), indent=2)}")
            print(f"{'='*70}\n")
            
            # Verify - should get 502 (not 400 or 500!)
            assert response["statusCode"] == 502, f"Expected 502, got {response['statusCode']}"
            assert response["headers"]["X-Error-Source"] == "AWS"
            
            body = json.loads(response["body"])
            assert "awsError" in body
            assert "unavailable" in body["awsError"].lower() or "unable" in body["awsError"].lower()
            
            print("✅ TEST 1 PASSED: Token failure returns 502")


def test_successful_call_FINAL():
    """
    ✅ Test successful SIRA call - returns 200
    """
    from function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        # Create successful mocks
        mock_token = MagicMock()
        mock_token.access_token = "valid-token-abc123"
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = mock_token
        mock_rotator.oauth.make_rtq_request.return_value = {
            "quoteId": "Q-12345",
            "status": "approved",
            "amount": 50000,
            "expiryDate": "2024-12-31"
        }
        
        with ExitStack() as stack:
            stack.enter_context(patch('function.validate'))
            stack.enter_context(patch('function.load_schema', return_value={}))
            stack.enter_context(patch('function.get_rotator', return_value=mock_rotator))
            stack.enter_context(patch('function.publish_to_kafka'))
            
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
            
            response = handler(event, {})
            
            print(f"\n{'='*70}")
            print(f"Status Code: {response['statusCode']}")
            print(f"Body: {json.dumps(json.loads(response['body']), indent=2)}")
            print(f"{'='*70}\n")
            
            # Verify success
            assert response["statusCode"] == 200
            
            body = json.loads(response["body"])
            assert "siraResponseJson" in body
            assert body["siraResponseJson"]["quoteId"] == "Q-12345"
            assert body["siraResponseJson"]["status"] == "approved"
            
            print("✅ TEST 2 PASSED: Successful SIRA call returns 200")


def test_http_error_from_synectics():
    """
    ✅ Test HTTP error from Synectics - returns error status
    """
    from function import handler
    import requests
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        # Create mock that fails at SIRA call
        mock_token = MagicMock()
        mock_token.access_token = "valid-token"
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = mock_token
        
        # Create HTTP error
        http_error = requests.exceptions.HTTPError("Bad Request")
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "type": "validation_error",
            "title": "Invalid Request",
            "status": 400,
            "detail": "Missing field"
        }
        http_error.response = mock_response
        
        mock_rotator.oauth.make_rtq_request.side_effect = http_error
        
        with ExitStack() as stack:
            stack.enter_context(patch('function.validate'))
            stack.enter_context(patch('function.load_schema', return_value={}))
            stack.enter_context(patch('function.get_rotator', return_value=mock_rotator))
            stack.enter_context(patch('function.publish_to_kafka'))
            
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
            
            response = handler(event, {})
            
            print(f"\n{'='*70}")
            print(f"Status Code: {response['statusCode']}")
            print(f"Headers: {response['headers']}")
            print(f"Body: {json.dumps(json.loads(response['body']), indent=2)}")
            print(f"{'='*70}\n")
            
            # Verify error handling
            assert response["statusCode"] == 400
            assert response["headers"]["X-Error-Source"] == "SYNECTICS"
            
            body = json.loads(response["body"])
            assert "synecticsError" in body
            
            print("✅ TEST 3 PASSED: HTTP error handled correctly")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("RUNNING ALL TESTS - FINAL VERSION")
    print("="*70 + "\n")
    
    try:
        test_token_failure_FINAL()
        test_successful_call_FINAL()
        test_http_error_from_synectics()
        
        print("\n" + "="*70)
        print("✅✅✅ ALL 3 TESTS PASSED! ✅✅✅")
        print("="*70)
        print("\nYour Lambda function tests are now working correctly!")
        print("No more 400 or 500 errors!")
        print("="*70 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED")
        print(f"Error: {e}\n")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR")
        print(f"Error: {e}\n")
        import traceback
        traceback.print_exc()