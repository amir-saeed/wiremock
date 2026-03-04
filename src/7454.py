# tests/test_config.py
import importlib
import pytest
import config


REQUIRED = {"DIRA_ASJSJ": "xyz-token", "API_KEY": "sk-abc123", "SECRET": "s3cr3t"}
FULL_ENV  = {**REQUIRED, "DATABASE_URL": "postgresql://u:p@localhost/db", "DEBUG": "true", "PORT": "9000"}


@pytest.fixture(autouse=True)
def _reload_config(monkeypatch):
    """Re-evaluate module-level vars after each env mutation."""
    for k, v in FULL_ENV.items():
        monkeypatch.setenv(k, v)
    importlib.reload(config)
    yield
    importlib.reload(config)


@pytest.mark.parametrize("key,expected", [
    ("DIRA_ASJSJ", "xyz-token"),
    ("API_KEY",    "sk-abc123"),
    ("SECRET",     "s3cr3t"),
    ("DATABASE_URL", "postgresql://u:p@localhost/db"),
])
def test_required_vars_loaded(key: str, expected: str) -> None:
    assert getattr(config, key) == expected


@pytest.mark.parametrize("debug_val,expected", [
    ("true",  True),
    ("True",  True),
    ("1",     False),  # only "true" (case-insensitive) is truthy per config logic
    ("false", False),
    ("",      False),
])
def test_debug_flag_coercion(monkeypatch, debug_val: str, expected: bool) -> None:
    monkeypatch.setenv("DEBUG", debug_val)
    importlib.reload(config)
    assert config.DEBUG is expected


@pytest.mark.parametrize("port_val,expected", [
    ("8000", 8000),
    ("443",  443),
])
def test_port_is_int(monkeypatch, port_val: str, expected: int) -> None:
    monkeypatch.setenv("PORT", port_val)
    importlib.reload(config)
    assert config.PORT == expected
    assert isinstance(config.PORT, int)


def test_database_url_defaults_to_sqlite(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    importlib.reload(config)
    assert config.DATABASE_URL == "sqlite:///:memory:"


def test_port_defaults_to_8000(monkeypatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    importlib.reload(config)
    assert config.PORT == 8000


@pytest.mark.parametrize("missing_key", REQUIRED.keys())
def test_missing_required_var_raises(monkeypatch, missing_key: str) -> None:
    monkeypatch.delenv(missing_key, raising=False)
    with pytest.raises(KeyError, match=missing_key):
        importlib.reload(config)