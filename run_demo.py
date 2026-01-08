#!/usr/bin/env python3
"""Quick start demo script"""

import time
import requests
from src.stub_loader import StubLoader

def wait_for_wiremock(max_retries=10):
    """Wait for WireMock to be ready"""
    url = "http://localhost:8080/__admin/mappings"
    for i in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("✓ WireMock is ready!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        print(f"Waiting for WireMock... ({i+1}/{max_retries})")
        time.sleep(2)
    print("✗ WireMock is not responding")
    return False

def main():
    print("=== WireMock Lambda Mock Demo ===\n")

    # Step 1: Check WireMock
    if not wait_for_wiremock():
        print("\n⚠ Please start WireMock first:")
        print("   docker compose up -d")
        return

    # Step 2: Load stubs
    print("\nLoading stubs...")
    loader = StubLoader(stub_dir="stubs")
    loader.reset_all()
    mappings = loader.load_from_config()
    print(f"✓ Loaded {len(mappings)} stubs\n")

    # Step 3: Test endpoints
    print("Testing Lambda invocations:\n")

    # Test 1: Successful order
    print("1. Testing successful order...")
    response = requests.post(
        "http://localhost:8080/2015-03-31/functions/order-processor/invocations",
        json={"status": "new", "customer_id": "CUST-001"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")

    # Test 2: Failed order
    print("2. Testing failed order...")
    response = requests.post(
        "http://localhost:8080/2015-03-31/functions/order-processor/invocations",
        json={"order_id": "FAIL-123"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")

    # Test 3: Payment
    print("3. Testing payment processing...")
    response = requests.post(
        "http://localhost:8080/2015-03-31/functions/payment-processor/invocations",
        json={"amount": 99.99, "currency": "USD"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")

    print("=== Demo Complete ===")

if __name__ == "__main__":
    main()