def test_base64_encoded_body():
    """Line 236: Base64 encoded request body"""
    from sira_integration.function import handler
    import base64
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        mock_token = MagicMock()
        mock_token.access_token = "valid-token"
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = mock_token
        mock_rotator.oauth.make_rtq_request.return_value = {"quoteId": "Q-B64"}
        
        with patch('sira_integration.function.validate'), \
             patch('sira_integration.function.load_schema', return_value={}), \
             patch('sira_integration.function.get_rotator', return_value=mock_rotator), \
             patch('sira_integration.function.publish_to_kafka'):
            
            body_json = json.dumps({
                "request": {
                    "header": {
                        "correlationid": "test-b64",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "quoteEntryTime": "2024-01-01T00:00:00Z",
                        "entityName": "TestEntity",
                        "status": "success"
                    },
                    "source": {
                        "sourceMessageId": "msg-b64",
                        "sourceData": "test data"
                    },
                    "WorkflowName": "TestWorkflow"
                }
            })
            
            # Encode body as base64
            encoded_body = base64.b64encode(body_json.encode()).decode()
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": True,  # THIS triggers line 236
                "body": encoded_body
            }
            
            response = handler(event, MockContext())
            
            assert response["statusCode"] == 200
            print("✅ BASE64 TEST PASSED - Covers line 236")


def test_body_not_dict():
    """Line 249: Request body is not a dict"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        event = {
            "httpMethod": "POST",
            "path": "/v1/sira",
            "headers": {"X-Consumer-Id": "test"},
            "isBase64Encoded": False,
            "body": json.dumps(["array", "not", "dict"])  # Array instead of object
        }
        
        response = handler(event, MockContext())
        
        assert response["statusCode"] == 500
        body = json.loads(response['body'])
        assert "must be a JSON object" in body['awsError']
        print("✅ BODY NOT DICT TEST PASSED - Covers line 249")


def test_schema_validation_error():
    """Line 262: Schema validation error"""
    from sira_integration.function import handler
    from jsonschema import ValidationError
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': 'http://test.com', 'ENABLE_KAFKA': 'false'}):
        
        with patch('sira_integration.function.validate') as mock_validate, \
             patch('sira_integration.function.load_schema', return_value={}):
            
            # Make validate raise ValidationError
            mock_validate.side_effect = ValidationError("Schema mismatch")
            
            event = {
                "httpMethod": "POST",
                "path": "/v1/sira",
                "headers": {"X-Consumer-Id": "test"},
                "isBase64Encoded": False,
                "body": json.dumps({
                    "request": {
                        "header": {
                            "correlationid": "test-schema",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "quoteEntryTime": "2024-01-01T00:00:00Z",
                            "entityName": "TestEntity",
                            "status": "success"
                        },
                        "source": {
                            "sourceMessageId": "msg-schema",
                            "sourceData": "test data"
                        },
                        "WorkflowName": "TestWorkflow"
                    }
                })
            }
            
            response = handler(event, MockContext())
            
            assert response["statusCode"] == 500
            body = json.loads(response['body'])
            assert "validation failed" in body['awsError'].lower()
            print("✅ SCHEMA VALIDATION ERROR TEST PASSED - Covers line 262")
