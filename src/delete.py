"""Test credential rotator with REAL AWS and OAuth provider."""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lambda"))

from src.oauth_jwt_service.core.secrets_manager import SecretsManagerClient
from src.oauth_jwt_service.core.oauth_client import OAuthClient
from src.oauth_jwt_service.core.token_cache import TokenCache
from src.oauth_jwt_service.core.credential_rotator import CredentialRotator
from src.oauth_jwt_service.config.settings import get_settings


def test_normal_flow():
    """Test 1: Normal flow - AWSCURRENT credentials work."""
    print("\n" + "=" * 60)
    print("TEST 1: Normal Flow (AWSCURRENT credentials)")
    print("=" * 60)
    
    settings = get_settings()
    
    # Initialize components
    secrets = SecretsManagerClient(settings.secret_name, settings.aws_region)
    oauth = OAuthClient()
    cache = TokenCache()
    rotator = CredentialRotator(secrets, oauth, cache)
    
    try:
        # First call - should fetch from Secrets Manager
        print("\n[1st Call] Fetching token...")
        token1 = rotator.get_valid_token()
        print(f"✅ Token acquired")
        print(f"   Access Token: {token1.access_token[:50]}...")
        print(f"   Expires At: {token1.expires_at}")
        print(f"   Is Expired: {token1.is_expired()}")
        
        # Second call - should use cache
        print("\n[2nd Call] Should use cache...")
        token2 = rotator.get_valid_token()
        print(f"✅ Token from cache")
        print(f"   Same token: {token1.access_token == token2.access_token}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_expiry():
    """Test 2: Cache returns None when token expired."""
    print("\n" + "=" * 60)
    print("TEST 2: Cache Expiry Check")
    print("=" * 60)
    
    from src.oauth_jwt_service.models.schemas import JWTToken
    
    cache = TokenCache()
    
    # Create an already-expired token
    expired_token = JWTToken(
        access_token="fake_expired_token",
        expires_in=10,  # 10 seconds
        issued_at=datetime(2024, 1, 1)  # Old date
    )
    
    cache.set(expired_token)
    print(f"Cached expired token: {expired_token.is_expired()}")
    
    # Try to get it back
    result = cache.get()
    if result is None:
        print("✅ Cache correctly returned None for expired token")
        return True
    else:
        print("❌ Cache returned expired token (should be None)")
        return False


def test_force_refresh():
    """Test 3: Clear cache and force new token."""
    print("\n" + "=" * 60)
    print("TEST 3: Force Refresh (Clear Cache)")
    print("=" * 60)
    
    settings = get_settings()
    
    secrets = SecretsManagerClient(settings.secret_name, settings.aws_region)
    oauth = OAuthClient()
    cache = TokenCache()
    rotator = CredentialRotator(secrets, oauth, cache)
    
    try:
        # Get token
        print("\n[1st Call] Get token...")
        token1 = rotator.get_valid_token()
        print(f"✅ Token 1: {token1.access_token[:30]}...")
        
        # Clear cache
        print("\n[Clear Cache]")
        cache.clear()
        print("✅ Cache cleared")
        
        # Get new token
        print("\n[2nd Call] Should fetch fresh token...")
        token2 = rotator.get_valid_token()
        print(f"✅ Token 2: {token2.access_token[:30]}...")
        
        # Tokens might be same or different depending on OAuth provider
        print(f"   Tokens identical: {token1.access_token == token2.access_token}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invalid_credentials():
    """Test 4: Test with invalid credentials (should fail gracefully)."""
    print("\n" + "=" * 60)
    print("TEST 4: Invalid Credentials (Expected to Fail)")
    print("=" * 60)
    
    from src.oauth_jwt_service.models.schemas import OAuthCredentials
    from pydantic import SecretStr
    
    oauth = OAuthClient()
    
    # Create fake invalid credentials
    fake_creds = OAuthCredentials(
        client_id="invalid_client_id",
        client_secret=SecretStr("invalid_secret"),
        token_url="https://httpbin.org/status/401",  # Returns 401
        audience="fake_audience"
    )
    
    try:
        print("\nAttempting with invalid credentials...")
        token = oauth.acquire_token(fake_creds)
        print(f"❌ Should have failed but got token: {token}")
        return False
        
    except Exception as e:
        print(f"✅ Correctly failed with: {e}")
        return True


def test_secrets_manager_connection():
    """Test 5: Verify Secrets Manager connectivity."""
    print("\n" + "=" * 60)
    print("TEST 5: AWS Secrets Manager Connection")
    print("=" * 60)
    
    settings = get_settings()
    
    try:
        secrets = SecretsManagerClient(settings.secret_name, settings.aws_region)
        print(f"\nSecret Name: {settings.secret_name}")
        print(f"Region: {settings.aws_region}")
        
        print("\nFetching AWSCURRENT credentials...")
        creds, metadata = secrets.get_credentials("AWSCURRENT")
        
        print(f"✅ Successfully retrieved credentials")
        print(f"   Version ID: {metadata.version_id}")
        print(f"   Version Stages: {metadata.version_stages}")
        print(f"   Client ID: {creds.client_id}")
        print(f"   Token URL: {creds.token_url}")
        print(f"   Audience: {creds.audience}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OAUTH JWT TOKEN ROTATION - REAL TESTS")
    print("=" * 60)
    
    # Check environment
    required_vars = [
        "AWS_REGION",
        "SECRET_NAME",
        "OAUTH_CLIENT_ID",
        "OAUTH_CLIENT_SECRET",
        "OAUTH_TOKEN_URL",
        "OAUTH_AUDIENCE",
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"\n❌ Missing environment variables: {missing}")
        print("Set them in .env or export them")
        return
    
    results = {
        "Secrets Manager Connection": test_secrets_manager_connection(),
        "Normal Flow": test_normal_flow(),
        "Cache Expiry": test_cache_expiry(),
        "Force Refresh": test_force_refresh(),
        "Invalid Credentials": test_invalid_credentials(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} passed")


if __name__ == "__main__":
    run_all_tests()