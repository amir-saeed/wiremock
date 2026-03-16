import json
import sira_integration.function as h
from unittest.mock import MagicMock

CTX = MagicMock()

VALID_EVENT = {
    "httpMethod": "POST",
    "path": "/sira/rtq",
    "headers": {"X-Consumer-Id": "mulesoft"},
    "isBase64Encoded": False,
    "body": json.dumps({
        "request": {
            "header": {
                "correlationid": "corr-123",
                "timestamp": "2024-01-01T00:00:00Z",
                "quoteEntryTime": "2024-01-01T00:00:00Z",
                "entityName": "Synectics",
                "status": "pending",
            },
            "source": {
                "sourceMessageId": "msg-001",
                "sourceData": '{"key":"value"}',
            },
            "WorkflowName": "TestWorkflow",
        }
    }),
}


def test_kafka_response_publish_exception_swallowed_lines_379_380(monkeypatch):
    """Lines 379-380: build_kafka_response_payload raises → swallowed, still returns 200."""
    monkeypatch.setattr(h, "SYNECTICS_RTQ_URL", "https://sira.example.com")
    monkeypatch.setattr(h, "ENABLE_KAFKA", True)
    monkeypatch.setattr(h, "mule_request_schema", {})
    monkeypatch.setattr(h, "validate", lambda **_: None)
    monkeypatch.setattr(h, "build_kafka_response_payload", lambda *_, **__: (_ for _ in ()).throw(RuntimeError("kafka boom")))

    rotator = MagicMock()
    token = MagicMock()
    token.access_token = "tok.header.payload.sig_abc123xyz"
    rotator.get_valid_token.return_value = token
    rotator.oauth.make_rtq_request.return_value = {"score": 99}
    monkeypatch.setattr(h, "get_rotator", lambda: rotator)

    resp = h.handler(VALID_EVENT, CTX)

    # Exception swallowed → still 200
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["siraResponseJson"] == {"score": 99}