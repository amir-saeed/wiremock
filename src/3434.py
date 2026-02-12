"""Step 1: Verify all environment variables are loaded correctly."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lambda"))


def test_step1_env_vars():
    """Verify all environment variables are set before running anything."""
    print("\n" + "=" * 60)
    print("STEP 1: Environment Variables Check")
    print("=" * 60)

    required = {
        "AWS_REGION":                   "AWS region",
        "SIRA_OAUTH_SECRET_NAME":       "Secrets Manager secret name",
        "SYNECTICS_TOKEN_URL":          "OAuth token URL",
        "OAUTH_GRANT_TYPE":             "OAuth grant type",
        "TOKEN_REFRESH_MARGIN_SECONDS": "Token refresh buffer",
        "ENABLE_KAFKA":                 "Kafka enabled flag",
        "KAFKA_BOOTSTRAP_SERVERS":      "Kafka brokers",
        "KAFKA_REQUEST_TOPIC":          "Kafka request topic",
        "KAFKA_RESPONSE_TOPIC":         "Kafka response topic",
        "ENVIRONMENT":                  "Environment (dev/staging/prod)",
        "USE_MOCK_SIRA":                "Mock SIRA flag",
    }

    all_good = True

    for var, description in required.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var:<35} = {value}  ({description})")
        else:
            print(f"❌ {var:<35} = MISSING  ({description})")
            all_good = False

    print("\n" + "=" * 60)
    print(f"Result: {'✅ All variables set - proceed to Step 2' if all_good else '❌ Fix missing variables first'}")
    print("=" * 60)

    return all_good


if __name__ == "__main__":
    passed = test_step1_env_vars()
    sys.exit(0 if passed else 1)