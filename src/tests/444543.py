def test_get_kafka_producer_no_bootstrap_servers():
    """Lines 94, 110-111: Kafka producer when no bootstrap servers"""
    from sira_integration.function import get_kafka_producer
    import sira_integration.function as func
    
    # Reset global
    func.kafka_producer = None
    
    with patch.dict(os.environ, {'KAFKA_BOOTSTRAP_SERVERS': ''}):
        result = get_kafka_producer()
        assert result is None
        print("✅ KAFKA NO SERVERS TEST PASSED - Covers line 94")


def test_get_kafka_producer_init_exception():
    """Lines 110-111: Kafka producer initialization fails"""
    from sira_integration.function import get_kafka_producer
    import sira_integration.function as func
    
    func.kafka_producer = None
    
    with patch.dict(os.environ, {'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092'}), \
         patch('sira_integration.function.KafkaProducer') as mock_kafka:
        
        mock_kafka.side_effect = Exception("Connection failed")
        result = get_kafka_producer()
        
        assert result is None
        print("✅ KAFKA INIT EXCEPTION TEST PASSED - Covers lines 110-111")


def test_kafka_value_serializer():
    """Lines 83-87: Kafka value serializer"""
    from sira_integration.function import kafka_value_serializer
    
    # Test bytes
    assert kafka_value_serializer(b"test") == b"test"
    
    # Test string
    assert kafka_value_serializer("test") == b"test"
    
    # Test dict
    result = kafka_value_serializer({"key": "value"})
    assert b"key" in result and b"value" in result
    
    print("✅ KAFKA SERIALIZER TEST PASSED - Covers lines 83-87")


def test_publish_kafka_disabled():
    """Lines 130-136: Publish to Kafka when disabled"""
    from sira_integration.function import publish_to_kafka
    
    with patch.dict(os.environ, {'ENABLE_KAFKA': 'false'}):
        # Should not raise exception
        publish_to_kafka("test-topic", {"data": "test"})
        print("✅ KAFKA DISABLED TEST PASSED - Covers lines 130-136")


def test_missing_synectics_url():
    """Line 241: Missing SYNECTICS_RTQ_URL"""
    from sira_integration.function import handler
    
    with patch.dict(os.environ, {'SYNECTICS_RTQ_URL': ''}):
        
        event = {
            "httpMethod": "POST",
            "path": "/v1/sira",
            "headers": {"X-Consumer-Id": "test"},
            "isBase64Encoded": False,
            "body": json.dumps({
                "request": {
                    "header": {
                        "correlationid": "test",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "quoteEntryTime": "2024-01-01T00:00:00Z",
                        "entityName": "TestEntity",
                        "status": "success"
                    },
                    "source": {
                        "sourceMessageId": "msg",
                        "sourceData": "data"
                    },
                    "WorkflowName": "Test"
                }
            })
        }
        
        response = handler(event, MockContext())
        
        assert response["statusCode"] == 500
        body = json.loads(response['body'])
        assert "SYNECTICS_RTQ_URL" in body['awsError']
        print("✅ MISSING URL TEST PASSED - Covers line 241")
