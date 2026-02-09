Step-by-Step Setup - No Bullshit
Step 1: Project Structure (2 min)
bashmkdir oauth-jwt-lambda && cd oauth-jwt-lambda
poetry init --no-interaction --name oauth-jwt-service --python "^3.12"

# Create folders
mkdir -p src/oauth_jwt_service/{core,models,config,utils} tests/unit
touch src/oauth_jwt_service/__init__.py lambda_handler.py

Step 2: Install Dependencies (1 min)
bashpoetry add boto3 pydantic pydantic-settings requests PyJWT tenacity cachetools kafka-python-ng
poetry add --group dev pytest pytest-mock moto[secretsmanager]
poetry install

Step 3: Models - Define Data Structures (5 min)
src/oauth_jwt_service/models/schemas.py
python"""What data looks like"""
from datetime import datetime, timedelta
from pydantic import BaseModel, SecretStr

class OAuthCredentials(BaseModel):
    """Username/password for OAuth"""
    client_id: str
    client_secret: SecretStr
    token_url: str
    scope: str | None = None

class JWTToken(BaseModel):
    """The actual token you get back"""
    access_token: str
    expires_in: int
    issued_at: datetime = datetime.utcnow()
    
    @property
    def expires_at(self) -> datetime:
        return self.issued_at + timedelta(seconds=self.expires_in)
    
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Is token dead or about to die?"""
        return datetime.utcnow() >= (self.expires_at - timedelta(seconds=buffer_seconds))
Test it:
bashpoetry run python -c "
from src.oauth_jwt_service.models.schemas import JWTToken
from datetime import datetime
t = JWTToken(access_token='abc123', expires_in=3600)
print(f'Expires at: {t.expires_at}')
print(f'Is expired: {t.is_expired()}')
"

Step 4: Config - Read Environment Variables (3 min)
src/oauth_jwt_service/config/settings.py
python"""Read settings from environment"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_name: str  # AWS secret name
    aws_region: str = "us-east-1"
    token_refresh_buffer_seconds: int = 300  # Refresh 5 min early
    
    class Config:
        env_prefix = "OAUTH_"  # Reads OAUTH_SECRET_NAME from env

def get_settings() -> Settings:
    return Settings()
Test it:
bashexport OAUTH_SECRET_NAME="my-oauth-secret"
export OAUTH_AWS_REGION="us-east-1"

poetry run python -c "
from src.oauth_jwt_service.config.settings import get_settings
s = get_settings()
print(f'Secret: {s.secret_name}, Region: {s.aws_region}')
"

Step 5: Secrets Manager - Get Credentials from AWS (5 min)
src/oauth_jwt_service/core/secrets_manager.py
python"""Fetch OAuth credentials from AWS Secrets Manager"""
import json
import boto3
from ..models.schemas import OAuthCredentials

class SecretsManagerClient:
    def __init__(self, secret_name: str, region: str):
        self.secret_name = secret_name
        self.client = boto3.client("secretsmanager", region_name=region)
    
    def get_credentials(self, stage: str = "AWSCURRENT") -> OAuthCredentials:
        """
        Get credentials from AWS
        stage = "AWSCURRENT" (active) or "AWSPENDING" (new/rotated)
        """
        response = self.client.get_secret_value(
            SecretId=self.secret_name,
            VersionStage=stage
        )
        data = json.loads(response["SecretString"])
        return OAuthCredentials(**data)
    
    def promote_pending_to_current(self, version_id: str) -> None:
        """Make AWSPENDING the new AWSCURRENT"""
        self.client.update_secret_version_stage(
            SecretId=self.secret_name,
            VersionStage="AWSCURRENT",
            MoveToVersionId=version_id
        )
Test it (mock):
bash# tests/unit/test_secrets_manager.py
from unittest.mock import Mock
from src.oauth_jwt_service.core.secrets_manager import SecretsManagerClient

def test_get_credentials():
    client = SecretsManagerClient("test-secret", "us-east-1")
    client.client = Mock()
    client.client.get_secret_value.return_value = {
        "SecretString": '{"client_id":"id","client_secret":"secret","token_url":"https://auth.com/token"}'
    }
    
    creds = client.get_credentials()
    assert creds.client_id == "id"

poetry run pytest tests/unit/test_secrets_manager.py -v

Step 6: OAuth Client - Get Token from Provider (5 min)
src/oauth_jwt_service/core/oauth_client.py
python"""Call OAuth provider to get JWT token"""
import requests
from ..models.schemas import OAuthCredentials, JWTToken

class OAuthClient:
    def acquire_token(self, credentials: OAuthCredentials) -> JWTToken:
        """POST to OAuth provider, get token back"""
        response = requests.post(
            credentials.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret.get_secret_value(),
                "scope": credentials.scope
            },
            timeout=30
        )
        
        if response.status_code == 401:
            raise Exception("Bad credentials")
        
        response.raise_for_status()
        return JWTToken(**response.json())

Step 7: Token Cache - Store Token in Memory (5 min)
src/oauth_jwt_service/core/token_cache.py
python"""Cache token so we don't request it every time"""
from cachetools import TTLCache
from ..models.schemas import JWTToken

class TokenCache:
    def __init__(self, ttl_seconds: int = 3600):
        self._cache = TTLCache(maxsize=10, ttl=ttl_seconds)
    
    def get(self) -> JWTToken | None:
        """Get cached token"""
        return self._cache.get("token")
    
    def set(self, token: JWTToken) -> None:
        """Save token to cache"""
        self._cache["token"] = token
    
    def clear(self) -> None:
        """Delete cached token"""
        self._cache.clear()

Step 8: Put It All Together - Main Logic (10 min)
src/oauth_jwt_service/core/credential_rotator.py
python"""Main logic: get token, handle rotation"""
from .secrets_manager import SecretsManagerClient
from .oauth_client import OAuthClient
from .token_cache import TokenCache
from ..models.schemas import JWTToken

class CredentialRotator:
    def __init__(self, secrets_manager, oauth_client, token_cache):
        self.secrets = secrets_manager
        self.oauth = oauth_client
        self.cache = token_cache
    
    def get_valid_token(self) -> JWTToken:
        """
        1. Check cache - return if valid
        2. Try AWSCURRENT credentials
        3. If AWSCURRENT fails, try AWSPENDING and promote it
        """
        # Check cache
        cached = self.cache.get()
        if cached and not cached.is_expired():
            return cached
        
        # Try AWSCURRENT
        try:
            creds = self.secrets.get_credentials("AWSCURRENT")
            token = self.oauth.acquire_token(creds)
            self.cache.set(token)
            return token
        except Exception as e:
            if "Bad credentials" not in str(e):
                raise
        
        # AWSCURRENT failed, try AWSPENDING
        creds = self.secrets.get_credentials("AWSPENDING")
        token = self.oauth.acquire_token(creds)
        
        # Success! Promote AWSPENDING to AWSCURRENT
        self.secrets.promote_pending_to_current("version_id_here")
        self.cache.set(token)
        return token

Step 9: Lambda Handler - Use It (5 min)
lambda_handler.py
python"""AWS Lambda entry point"""
from src.oauth_jwt_service.core.secrets_manager import SecretsManagerClient
from src.oauth_jwt_service.core.oauth_client import OAuthClient
from src.oauth_jwt_service.core.token_cache import TokenCache
from src.oauth_jwt_service.core.credential_rotator import CredentialRotator

# Global = reused across Lambda invocations
_rotator = None

def lambda_handler(event, context):
    global _rotator
    
    # Initialize once per container
    if _rotator is None:
        secrets = SecretsManagerClient("my-oauth-secret", "us-east-1")
        oauth = OAuthClient()
        cache = TokenCache()
        _rotator = CredentialRotator(secrets, oauth, cache)
    
    # Get token (uses cache if valid)
    token = _rotator.get_valid_token()
    
    # Use token for Kafka/API calls
    return {
        "statusCode": 200,
        "body": f"Token: {token.access_token[:20]}..."
    }

Step 10: Test Locally (2 min)
bash# Set fake AWS creds for local testing
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export OAUTH_SECRET_NAME=test-secret

poetry run pytest tests/ -v