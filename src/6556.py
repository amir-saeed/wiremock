"""Step 2: Verify AWS Secrets Manager connection and credentials."""

import os
import sys
import json
import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lambda"))

from src.oauth_jwt_service.models.schemas import OAuthCredentials


def test_step2_secrets_manager():
    """Verify AWS Secrets Manager connection and validate secret JSON structure."""
    print("\n" + "=" * 60)
    print("STEP 2: AWS Secrets Manager Connection")
    print("=" * 60)

    secret_name = os.getenv("SIRA_OAUTH_SECRET_NAME")
    region      = os.getenv("AWS_REGION")

    print(f"\nSecret Name : {secret_name}")
    print(f"Region      : {region}")

    client = boto3.client("secretsmanager", region_name=region)

    # ── Test 1: SIRA_CURRENT ──────────────────────────────────────
    print("\n--- Test 2a: Fetch SIRA_CURRENT ---")
    try:
        response = client.get_secret_value(
            SecretId=secret_name,
            VersionStage="SIRA_CURRENT"
        )
        data = json.loads(response["SecretString"])

        print(f"✅ SIRA_CURRENT fetched successfully")
        print(f"   Version ID     : {response['VersionId']}")
        print(f"   Version Stages : {response.get('VersionStages')}")

        # Validate with Pydantic
        creds = OAuthCredentials(**data)
        print(f"✅ Pydantic validation passed")
        print(f"   client_id      : {creds.client_id}")
        print(f"   token_url      : {creds.token_url}")
        print(f"   audience       : {creds.audience}")
        print(f"   cached_jwt     : {'Present' if creds.cached_jwt else 'None'}")
        print(f"   jwt_expires_at : {creds.cached_jwt_expires_at}")

    except ClientError as e:
        print(f"❌ SIRA_CURRENT failed: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Pydantic validation failed: {e}")
        return False

    # ── Test 2: SIRA_NEXT ─────────────────────────────────────────
    print("\n--- Test 2b: Fetch SIRA_NEXT (optional) ---")
    try:
        response = client.get_secret_value(
            SecretId=secret_name,
            VersionStage="SIRA_NEXT"
        )
        data = json.loads(response["SecretString"])

        creds_next = OAuthCredentials(**data)
        print(f"✅ SIRA_NEXT fetched successfully")
        print(f"   Version ID     : {response['VersionId']}")
        print(f"   client_id      : {creds_next.client_id}")
        print(f"   cached_jwt     : {'Present' if creds_next.cached_jwt else 'None'}")

    except ClientError as e:
        # SIRA_NEXT not existing is acceptable
        print(f"⚠️  SIRA_NEXT not found: {e.response['Error']['Code']} (this is OK)")

    except Exception as e:
        print(f"❌ SIRA_NEXT Pydantic validation failed: {e}")
        return False

    # ── Test 3: Required JSON fields ──────────────────────────────
    print("\n--- Test 2c: Required Secret Fields ---")
    required_fields = ["client_id", "client_secret", "token_url", "audience"]
    all_fields_ok   = True

    for field in required_fields:
        if data.get(field):
            print(f"✅ {field:<25} = present")
        else:
            print(f"❌ {field:<25} = MISSING in secret JSON")
            all_fields_ok = False

    optional_fields = ["cached_jwt", "cached_jwt_expires_at"]
    for field in optional_fields:
        value = data.get(field)
        print(f"{'✅' if value else '⚠️ '} {field:<25} = {value if value else 'null (will be set after first OAuth call)'}")

    print("\n" + "=" * 60)
    print(f"Result: {'✅ Secrets Manager OK - proceed to Step 3' if all_fields_ok else '❌ Fix secret JSON structure first'}")
    print("=" * 60)

    return all_fields_ok


if __name__ == "__main__":
    passed = test_step2_secrets_manager()
    sys.exit(0 if passed else 1)