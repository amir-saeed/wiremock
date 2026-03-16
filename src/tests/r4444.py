@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    h.kafka_producer = None
    monkeypatch.setattr(h, "KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
    yield
    h.kafka_producer = None
 
 
def test_get_kafka_producer_success_lines_112_113(monkeypatch):
    """Lines 112-113: KafkaProducer constructs OK → logged + returned."""
    fake_producer = MagicMock()
    monkeypatch.setattr(h, "KafkaProducer", lambda **_: fake_producer)
 
    result = h.get_kafka_producer()
 
    assert result is fake_producer
    assert h.kafka_producer is fake_producer  # cached globally