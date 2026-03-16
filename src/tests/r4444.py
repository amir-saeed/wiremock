import sira_integration.function as h
from unittest.mock import MagicMock
import pytest


@pytest.fixture(autouse=True)
def _kafka_enabled(monkeypatch):
    monkeypatch.setattr(h, "ENABLE_KAFKA", True)
    h.kafka_producer = None


def test_publish_send_and_flush_success_lines_132_136(monkeypatch):
    """Lines 132-136: producer.send + flush called successfully."""
    producer = MagicMock()
    monkeypatch.setattr(h, "get_kafka_producer", lambda: producer)

    h.publish_to_kafka("test-topic", {"data": "payload"})

    producer.send.assert_called_once_with("test-topic", value={"data": "payload"})
    producer.flush.assert_called_once_with(timeout=5)


def test_publish_send_exception_swallowed_lines_138_139(monkeypatch):
    """Lines 138-139: producer.send raises → swallowed, no exception propagates."""
    producer = MagicMock()
    producer.send.side_effect = RuntimeError("broker unavailable")
    monkeypatch.setattr(h, "get_kafka_producer", lambda: producer)

    h.publish_to_kafka("test-topic", {"data": "payload"})  # must not raise