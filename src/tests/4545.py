def test_kafka_bootstrap_servers_missing_returns_none(valid_request_body, monkeypatch):
    """When KAFKA_BOOTSTRAP_SERVERS not set, get_kafka_producer returns None."""
    # Enable Kafka but don't set bootstrap servers
    monkeypatch.setattr("sira_integration.function.ENABLE_KAFKA", True)
    monkeypatch.setattr("sira_integration.function.KAFKA_BOOTSTRAP_SERVERS", "")  # Empty
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    monkeypatch.setattr("sira_integration.function.SIRA_TIMEOUT_SECONDS", 10.0)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator:
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        mock_rotator.oauth.make_rtq_request.return_value = {"resultStatus": "CLEAR"}
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        # Still succeeds even though Kafka publish fails
        assert result["statusCode"] == 200
def test_kafka_producer_init_fails_continues(valid_request_body, monkeypatch):
    """When KafkaProducer fails to initialize, Lambda continues without Kafka."""
    monkeypatch.setattr("sira_integration.function.ENABLE_KAFKA", True)
    monkeypatch.setattr("sira_integration.function.KAFKA_BOOTSTRAP_SERVERS", "broker1:9092")
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    monkeypatch.setattr("sira_integration.function.SIRA_TIMEOUT_SECONDS", 10.0)
    
    with patch("sira_integration.function.get_rotator") as mock_get_rotator, \
         patch("sira_integration.function.KafkaProducer") as mock_kafka_producer:
        
        # Kafka producer init fails
        mock_kafka_producer.side_effect = Exception("Failed to initialize Kafka producer")
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        mock_rotator.oauth.make_rtq_request.return_value = {"resultStatus": "CLEAR"}
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        # Lambda continues despite Kafka failure
        assert result["statusCode"] == 200

def test_publish_kafka_when_producer_unavailable(valid_request_body, monkeypatch):
    """When Kafka producer unavailable, publish_to_kafka logs and skips."""
    monkeypatch.setattr("sira_integration.function.ENABLE_KAFKA", True)
    monkeypatch.setattr("sira_integration.function.SYNECTICS_RTQ_URL", "http://localhost:8080/sira/rtq")
    monkeypatch.setattr("sira_integration.function.SIRA_TIMEOUT_SECONDS", 10.0)
    
    with patch("sira_integration.function.get_kafka_producer") as mock_get_producer, \
         patch("sira_integration.function.get_rotator") as mock_get_rotator:
        
        # get_kafka_producer returns None (producer unavailable)
        mock_get_producer.return_value = None
        
        mock_rotator = MagicMock()
        mock_rotator.get_valid_token.return_value = MagicMock(access_token="TOKEN")
        mock_rotator.oauth.make_rtq_request.return_value = {"resultStatus": "CLEAR"}
        mock_get_rotator.return_value = mock_rotator
        
        event = build_event(valid_request_body)
        result = lambda_handler(event, MockContext())
        
        # Lambda succeeds, Kafka publish was skipped
        assert result["statusCode"] == 200