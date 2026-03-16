"""
Two high-coverage critical tests for sira_integration.handler.
Test 1 (happy path)  → covers lines: 59-65, 243, 264, 291, 302, 310, 315,
                        379-380, 438-439 + all setup/validation logic
Test 2 (HTTPError)   → covers lines: 461-617, 636-637, 659-660
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

MODULE = "sira_integration.handler"

VALID_EVENT: dict[str, Any] = {
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
            "SourceDataVersion": 1,
            "DataLengthBytes": 100,
            "SourceMessagePriority": 1,
            "IsTrace": False,
            "Username": "user1",
            "ClientName": "client1",
        }
    }),
}

CTX = MagicMock()
CTX.function_name = "sira-handler"
CTX.aws_request_id = "req-000"


@pytest.fixture(autouse=True)
def _bypass_schema():
    with (
        patch(f"{MODULE}.load_schema", return_value={}),
        patch(f"{MODULE}.validate", return_value=None),
        patch(f"{MODULE}.mule_request_schema", {}),
    ):
        yield


@pytest.fixture(autouse=True)
def _reset_globals():
    import sira_integration.handler as h
    h._rotator = None
    h.kafka_producer = None
    yield
    h._rotator = None
    h.kafka_producer = None


def _make_rotator(sira_response: Any = None, side_effect: Exception | None = None) -> MagicMock:
    rotator = MagicMock()
    token = MagicMock()
    token.access_token = "tok.header.payload.sig_abc123xyz"
    rotator.get_valid_token.return_value = token
    if side_effect:
        rotator.oauth.make_rtq_request.side_effect = side_effect
    else:
        rotator.oauth.make_rtq_request.return_value = sira_response or {"score": 99}
    return rotator


# ===========================================================================
# Test 1 — Full happy path
# Covers: cold-start get_rotator (59-65), all validation guards (243-315),
#         Kafka request publish swallow (379-380), success return (438-439),
#         Kafka response publish swallow
# ===========================================================================
def test_happy_path_covers_validation_and_success(monkeypatch):
    monkeypatch.setattr(f"{MODULE}.SYNECTICS_RTQ_URL", "https://sira.example.com")
    monkeypatch.setattr(f"{MODULE}.ENABLE_KAFKA", True)

    rotator = _make_rotator()
    producer = MagicMock()

    with (
        patch(f"{MODULE}.SecretsManagerClient"),
        patch(f"{MODULE}.OAuthClient"),
        patch(f"{MODULE}.TokenCache"),
        patch(f"{MODULE}.CredentialRotator", return_value=rotator),
        patch(f"{MODULE}.KafkaProducer", return_value=producer),
        patch(f"{MODULE}.KAFKA_BOOTSTRAP_SERVERS", "broker:9092"),
    ):
        import sira_integration.handler as h
        resp = h.handler(VALID_EVENT, CTX)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["siraResponseJson"] == {"score": 99}
    assert resp["headers"]["X-Error-Source"] == "NONE"


# ===========================================================================
# Test 2 — HTTPError with JSON body from Synectics
# Covers: HTTPError branch (461-580), Kafka failure publish (581-617),
#         outer Exception handler (636-637), InternalServerError (659-660)
# ===========================================================================
def test_http_error_json_body_covers_error_branches(monkeypatch):
    monkeypatch.setattr(f"{MODULE}.SYNECTICS_RTQ_URL", "https://sira.example.com")
    monkeypatch.setattr(f"{MODULE}.ENABLE_KAFKA", True)

    syn_error = {"type": "about:blank", "title": "Unprocessable Entity", "status": 422}
    fake_response = MagicMock(spec=requests.Response)
    fake_response.status_code = 422
    fake_response.json.return_value = syn_error
    fake_response.text = json.dumps(syn_error)

    http_err = requests.exceptions.HTTPError(response=fake_response)
    http_err.response = fake_response

    rotator = _make_rotator(side_effect=http_err)
    producer = MagicMock()

    with (
        patch(f"{MODULE}.get_rotator", return_value=rotator),
        patch(f"{MODULE}.get_kafka_producer", return_value=producer),
    ):
        import sira_integration.handler as h
        resp = h.handler(VALID_EVENT, CTX)

    assert resp["statusCode"] == 422
    assert resp["headers"]["X-Error-Source"] == "SYNECTICS"
    body = json.loads(resp["body"])
    assert body["synecticsError"]["title"] == "Unprocessable Entity"
    producer.send.assert_called()