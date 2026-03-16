def test_kafka_failure_publish_exception_swallowed_lines_438_439(monkeypatch):
    """Lines 438-439: publish_to_kafka raises inside HTTPError block → swallowed, still returns upstream status."""
    monkeypatch.setattr(h, "SYNECTICS_RTQ_URL", "https://sira.example.com")
    monkeypatch.setattr(h, "ENABLE_KAFKA", True)
    monkeypatch.setattr(h, "mule_request_schema", {})
    monkeypatch.setattr(h, "validate", lambda **_: None)
    monkeypatch.setattr(h, "publish_to_kafka", MagicMock(side_effect=RuntimeError("kafka boom")))
 
    # Build HTTPError with JSON body
    fake_resp = MagicMock(spec=requests.Response)
    fake_resp.status_code = 422
    fake_resp.json.return_value = {"title": "Unprocessable Entity", "status": 422}
    fake_resp.text = '{"title":"Unprocessable Entity","status":422}'
    http_err = requests.exceptions.HTTPError(response=fake_resp)
    http_err.response = fake_resp
 
    rotator = MagicMock()
    token = MagicMock()
    token.access_token = "tok.header.payload.sig_abc123xyz"
    rotator.get_valid_token.return_value = token
    rotator.oauth.make_rtq_request.side_effect = http_err
    monkeypatch.setattr(h, "get_rotator", lambda: rotator)
 
    resp = h.handler(VALID_EVENT, CTX)
 
    # Exception swallowed → still propagates Synectics status
    assert resp["statusCode"] == 422
    assert resp["headers"]["X-Error-Source"] == "SYNECTICS"