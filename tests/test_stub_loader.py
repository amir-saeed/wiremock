import pytest
import requests
from src.stub_loader import StubLoader

WIREMOCK_URL = "http://localhost:8080"

@pytest.fixture(scope="function")
def stub_loader():
    loader = StubLoader(stub_dir="stubs")
    loader.reset_all()
    yield loader
    loader.reset_all()

def invoke_lambda(function_name: str, payload: dict) -> dict:
    url = f"{WIREMOCK_URL}/2015-03-31/functions/{function_name}/invocations"
    response = requests.post(url, json=payload)
    return {"status_code": response.status_code, "body": response.json()}

def test_load_single_stub_file(stub_loader):
    stub_loader.create_stub_from_file(
        function_name="order-processor",
        response_file="orders/success.json",
        status_code=200
    )
    result = invoke_lambda("order-processor", {"customer_id": "CUST-123", "status": "new"})
    assert result["status_code"] == 200
    assert result["body"]["body"]["status"] == "CONFIRMED"

def test_load_all_stubs_from_config(stub_loader):
    mappings = stub_loader.load_from_config()
    assert len(mappings) > 0
    result = invoke_lambda("order-processor", {"status": "new", "customer_id": "CUST-001"})
    assert result["status_code"] == 200
    assert result["body"]["body"]["status"] == "CONFIRMED"
    result = invoke_lambda("order-processor", {"order_id": "FAIL-001"})
    assert result["status_code"] == 400
    assert "ValidationException" in result["body"]["body"]["errorType"]

def test_load_directory_as_stubs(stub_loader):
    mappings = stub_loader.load_directory_as_stubs(
        function_name="payment-processor", directory="payments"
    )
    assert len(mappings) >= 2
    result = invoke_lambda("payment-processor", {"scenario": "authorized", "amount": 100})
    assert result["status_code"] == 200

def test_list_all_stubs(stub_loader):
    all_stubs = stub_loader.get_all_stub_files()
    assert "orders" in all_stubs
    assert "payments" in all_stubs
    assert len(all_stubs["orders"]) >= 3

def test_dynamic_response_templating(stub_loader):
    stub_loader.create_stub_from_file(
        function_name="order-processor", response_file="orders/success.json"
    )
    result = invoke_lambda("order-processor", {"customer_id": "CUST-DYNAMIC-123"})
    body = result["body"]["body"]
    assert body["customer_id"] == "CUST-DYNAMIC-123"
    assert "order_id" in body
    assert "created_at" in body
