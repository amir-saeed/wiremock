def test_get_rotator_cold_start(monkeypatch):
    h._rotator = None  # ensure cold start
 
    fake_rotator = MagicMock()
    monkeypatch.setattr(h, "SecretsManagerClient", MagicMock())
    monkeypatch.setattr(h, "OAuthClient", MagicMock())
    monkeypatch.setattr(h, "TokenCache", MagicMock())
    monkeypatch.setattr(h, "CredentialRotator", lambda **_: fake_rotator)
 
    result = h.get_rotator()
 
    assert result is fake_rotator
    assert h._rotator is fake_rotator  # cached for next call