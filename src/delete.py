"""Environment variables - single source of truth."""

import os


def _require(key: str) -> str:
    """Fail fast on startup if required variable is missing."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value


# AWS
AWS_REGION = _require("AWS_REGION")
SECRET_NAME = _require("SECRET_NAME")

# OAuth
OAUTH_CLIENT_ID     = _require("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = _require("OAUTH_CLIENT_SECRET")
OAUTH_TOKEN_URL     = _require("OAUTH_TOKEN_URL")
OAUTH_AUDIENCE      = _require("OAUTH_AUDIENCE")
OAUTH_SCOPE         = os.getenv("OAUTH_SCOPE", "")
OAUTH_GRANT_TYPE    = os.getenv("OAUTH_GRANT_TYPE", "client_credentials")

# Token
TOKEN_REFRESH_BUFFER_SECONDS = int(os.getenv("TOKEN_REFRESH_BUFFER_SECONDS", "300"))
TOKEN_MAX_AGE_SECONDS        = int(os.getenv("TOKEN_MAX_AGE_SECONDS", "3600"))

# Kafka
KAFKA_BOOTSTRAP_SERVERS = _require("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC             = _require("KAFKA_TOPIC")
KAFKA_ENABLE_SSL        = os.getenv("KAFKA_ENABLE_SSL", "true").lower() == "true"

# App
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
ENVIRONMENT     = os.getenv("ENVIRONMENT", "dev")
ENABLE_METRICS  = os.getenv("ENABLE_METRICS", "true").lower() == "true"