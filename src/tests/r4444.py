import json
import sira_integration.function as h
from unittest.mock import MagicMock
import pytest


@pytest.fixture(autouse=True)
def _bypass_schema(monkeypatch):
    monkeypatch.setattr(h, "SYNECTICS_RTQ_URL", "https://sira.example.com")
    monkeypatch.setattr(h, "ENABLE_KAFKA", False)
    monkeypatch.setattr(h, "mule_request_schema", {})
    monkeypatch.setattr(h, "validate", lambda **_: None)


CTX = MagicMock()


def test_invalid_json_body_lines_247_248():
    """Lines 247-248: JSONDecodeError → handler returns 500 with awsError."""
    event = {
        "httpMethod": "POST",
        "path": "/sira/rtq",
        "headers": {},
        "isBase64Encoded": False,
        "body": "NOT_VALID_JSON{{{{",
    }

    resp = h.handler(event, CTX)

    assert resp["statusCode"] == 500
    assert "awsError" in json.loads(resp["body"])