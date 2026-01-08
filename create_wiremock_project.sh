#!/usr/bin/env bash
set -euo pipefail

mkdir -p src stubs/orders stubs/payments stubs/customers tests

# pyproject.toml (Poetry, Python 3.12)
cat > pyproject.toml << 'PYTOML'
[tool.poetry]
name = "wiremock"
version = "0.1.0"
description = "WireMock-based local mocking for AWS Lambda invoke endpoints with JSON stub templates"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{ include = "src" }]

[tool.poetry.dependencies]
python = "^3.12"
wiremock = ">=2.6.1,<3.0.0"
requests = ">=2.31.0"
PyYAML = ">=6.0.1"

[tool.poetry.group.dev.dependencies]
pytest = ">=7.4"

[tool.pytest.ini_options]
addopts = "-q"
python_files = ["tests/test_*.py"]

[build-system]
requires = ["poetry-core>=1.8.0"]
build-backend = "poetry.core.masonry.api"
PYTOML

# README
cat > README.md << 'README'
# wiremock
Mock AWS Lambda invoke endpoints using WireMock with JSON stub responses and templating.

Requirements:
- Python 3.12
- Docker + Docker Compose
- Poetry

Setup:
- docker compose up -d
- poetry env use python3.12
- poetry install

Run tests:
- poetry run pytest
README

# docker-compose.yml
cat > docker-compose.yml << 'DOCKER'
version: '3.8'

services:
  wiremock:
    image: wiremock/wiremock:3.3.1
    ports:
      - "8080:8080"
    volumes:
      - ./stubs:/home/wiremock/stubs:ro
    command:
      - --global-response-templating
      - --verbose
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/__admin/"]
      interval: 10s
      timeout: 5s
      retries: 5
DOCKER

# src/__init__.py
cat > src/__init__.py << 'PY'
# src package
PY

# src/stub_loader.py
cat > src/stub_loader.py << 'PY'
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from wiremock.client import Mappings, HttpMethods, Mapping
from wiremock.resources.mappings import MappingRequest, MappingResponse
from wiremock.constants import Config

class StubLoader:
    """Load and manage JSON stub files with WireMock"""

    def __init__(
        self,
        stub_dir: str = "stubs",
        host: str = "localhost",
        port: int = 8080
    ):
        self.stub_dir = Path(stub_dir)
        self.mappings_file = self.stub_dir / "mappings.yaml"

        Config.base_url = f"http://{host}:{port}/__admin"
        self.mappings = Mappings()

    def load_json_file(self, relative_path: str) -> Dict[str, Any]:
        file_path = self.stub_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Stub file not found: {file_path}")
        with open(file_path, 'r') as f:
            return json.load(f)

    def load_all_json_files(self, subdirectory: str = "") -> Dict[str, Dict]:
        search_path = self.stub_dir / subdirectory if subdirectory else self.stub_dir
        json_files: Dict[str, Dict[str, Any]] = {}
        for json_file in search_path.rglob("*.json"):
            relative_path = json_file.relative_to(self.stub_dir)
            key = str(relative_path.with_suffix("")).replace("/", "_")
            json_files[key] = self.load_json_file(str(relative_path))
        return json_files

    def _build_request_matcher(
        self,
        function_name: str,
        request_match: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url_pattern = f"/2015-03-31/functions/{function_name}/invocations"
        request_config: Dict[str, Any] = {
            "method": HttpMethods.POST,
            "urlPathEqualTo": url_pattern
        }
        if not request_match:
            return request_config

        if "body_contains" in request_match:
            request_config["bodyPatterns"] = [{"contains": request_match["body_contains"]}]

        if "body_json" in request_match:
            patterns = []
            for key, value in request_match["body_json"].items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        if op == "less_than":
                            patterns.append({"matchesJsonPath": f"$[?(@.{key} < {val})]"})
                        elif op == "greater_than":
                            patterns.append({"matchesJsonPath": f"$[?(@.{key} > {val})]"})
                        elif op == "equals":
                            patterns.append({"matchesJsonPath": f"$[?(@.{key} == '{val}')]"})
                else:
                    patterns.append({
                        "equalToJson": json.dumps({key: value}),
                        "ignoreArrayOrder": True,
                        "ignoreExtraElements": True
                    })
            request_config["bodyPatterns"] = patterns

        if "headers" in request_match:
            request_config["headers"] = {k: {"equalTo": v} for k, v in request_match["headers"].items()}

        if "query_params" in request_match:
            request_config["queryParameters"] = {k: {"equalTo": v} for k, v in request_match["query_params"].items()}

        return request_config

    def create_stub_from_file(
        self,
        function_name: str,
        response_file: str,
        status_code: int = 200,
        delay_ms: int = 0,
        priority: int = 5,
        request_match: Optional[Dict[str, Any]] = None
    ) -> Mapping:
        response_body = self.load_json_file(response_file)
        request_config = self._build_request_matcher(function_name, request_match)
        response_config: Dict[str, Any] = {
            "status": status_code,
            "jsonBody": response_body,
            "headers": {
                "Content-Type": "application/json",
                "x-amzn-RequestId": "{{randomValue type='UUID'}}",
            },
            "transformers": ["response-template"]
        }
        if delay_ms > 0:
            response_config["fixedDelayMilliseconds"] = delay_ms
        mapping = Mapping(
            priority=priority,
            request=MappingRequest(**request_config),
            response=MappingResponse(**response_config)
        )
        return self.mappings.create_mapping(mapping)

    def load_from_config(self) -> List[Mapping]:
        if not self.mappings_file.exists():
            raise FileNotFoundError(f"Mappings config not found: {self.mappings_file}")
        with open(self.mappings_file, 'r') as f:
            config = yaml.safe_load(f)
        created_mappings: List[Mapping] = []
        for stub_config in config.get("stubs", []):
            mapping = self.create_stub_from_file(
                function_name=stub_config["function_name"],
                response_file=stub_config["response_file"],
                status_code=stub_config.get("status_code", 200),
                delay_ms=stub_config.get("delay_ms", 0),
                priority=stub_config.get("priority", 5),
                request_match=stub_config.get("request_match")
            )
            created_mappings.append(mapping)
        return created_mappings

    def load_directory_as_stubs(
        self,
        function_name: str,
        directory: str,
        base_priority: int = 10
    ) -> List[Mapping]:
        search_path = self.stub_dir / directory
        created_mappings: List[Mapping] = []
        for idx, json_file in enumerate(sorted(search_path.glob("*.json"))):
            relative_path = json_file.relative_to(self.stub_dir)
            filename_stem = json_file.stem
            mapping = self.create_stub_from_file(
                function_name=function_name,
                response_file=str(relative_path),
                priority=base_priority + idx,
                request_match={"body_contains": f'\"scenario\": \"{filename_stem}\"'}
            )
            created_mappings.append(mapping)
        return created_mappings

    def reset_all(self) -> None:
        self.mappings.delete_all_mappings()

    def get_all_stub_files(self) -> Dict[str, List[str]]:
        stubs_by_category: Dict[str, List[str]] = {}
        for json_file in self.stub_dir.rglob("*.json"):
            relative_path = json_file.relative_to(self.stub_dir)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
            if category not in stubs_by_category:
                stubs_by_category[category] = []
            stubs_by_category[category].append(str(relative_path))
        return stubs_by_category
PY

# src/stub_generator.py
cat > src/stub_generator.py << 'PY'
from pathlib import Path
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random

class StubGenerator:
    """Generate multiple stub files programmatically"""

    def __init__(self, output_dir: str = "stubs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_order_stubs(self, count: int = 10):
        orders_dir = self.output_dir / "orders" / "generated"
        orders_dir.mkdir(parents=True, exist_ok=True)
        statuses = ["CONFIRMED", "PENDING", "PROCESSING", "SHIPPED", "DELIVERED"]
        for i in range(count):
            order_data: Dict[str, Any] = {
                "statusCode": 200,
                "body": {
                    "order_id": f"ORD-GEN-{i:04d}",
                    "customer_id": f"CUST-{random.randint(1000, 9999)}",
                    "status": random.choice(statuses),
                    "items": [
                        {
                            "sku": f"PROD-{random.randint(100, 999)}",
                            "quantity": random.randint(1, 5),
                            "price": round(random.uniform(10, 500), 2)
                        }
                        for _ in range(random.randint(1, 3))
                    ],
                    "total_amount": round(random.uniform(50, 1000), 2),
                    "currency": "USD",
                    "created_at": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                    "metadata": {
                        "warehouse": random.choice(["US-EAST", "US-WEST", "EU-CENTRAL"]),
                        "priority": random.choice(["standard", "express", "overnight"])
                    }
                }
            }
            filename = orders_dir / f"order_{i:04d}.json"
            with open(filename, 'w') as f:
                json.dump(order_data, f, indent=2)

    def generate_error_stubs(self):
        errors_dir = self.output_dir / "errors"
        errors_dir.mkdir(parents=True, exist_ok=True)
        error_types = [
            ("ValidationException", "Invalid request data", 400),
            ("NotFoundException", "Resource not found", 404),
            ("UnauthorizedException", "Invalid credentials", 401),
            ("ForbiddenException", "Access denied", 403),
            ("ThrottlingException", "Rate limit exceeded", 429),
            ("InternalServerError", "Internal server error", 500),
            ("ServiceUnavailable", "Service temporarily unavailable", 503),
            ("TimeoutException", "Request timeout", 504),
        ]
        for error_type, message, status in error_types:
            error_data: Dict[str, Any] = {
                "statusCode": status,
                "body": {
                    "errorType": error_type,
                    "errorMessage": message,
                    "timestamp": "{{now}}",
                    "request_id": "{{randomValue type='UUID'}}",
                    "details": {
                        "code": f"ERR-{status}",
                        "retry_after": 5 if status == 429 else None
                    }
                }
            }
            filename = errors_dir / f"{error_type.lower()}.json"
            with open(filename, 'w') as f:
                json.dump(error_data, f, indent=2)

if __name__ == "__main__":
    generator = StubGenerator()
    generator.generate_order_stubs(count=50)
    generator.generate_error_stubs()
    print("Generated stubs successfully!")
PY

# src/wiremock_client.py
cat > src/wiremock_client.py << 'PY'
from wiremock.constants import Config
from wiremock.client import Admin

def ping_admin() -> bool:
    try:
        return Admin.get_admin().get_root() is not None
    except Exception:
        return False

def set_admin_base_url(host: str = "localhost", port: int = 8080) -> None:
    Config.base_url = f"http://{host}:{port}/__admin"
PY

# src/models.py
cat > src/models.py << 'PY'
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class LambdaInvocation:
    function_name: str
    payload: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None
PY

# stubs/mappings.yaml
cat > stubs/mappings.yaml << 'YAML'
stubs:
  - function_name: "order-processor"
    priority: 1
    request_match:
      body_contains: '"status": "new"'
    response_file: "orders/success.json"
    status_code: 200
    delay_ms: 100

  - function_name: "order-processor"
    priority: 2
    request_match:
      body_contains: '"status": "retry"'
    response_file: "orders/pending.json"
    status_code: 202
    delay_ms: 200

  - function_name: "order-processor"
    priority: 3
    request_match:
      body_contains: '"order_id": "FAIL"'
    response_file: "orders/failed.json"
    status_code: 400

  - function_name: "payment-processor"
    priority: 1
    request_match:
      body_json:
        amount:
          less_than: 10000
    response_file: "payments/authorized.json"
    status_code: 200
    delay_ms: 150

  - function_name: "payment-processor"
    priority: 2
    request_match:
      body_json:
        card_type: "FRAUD_TEST"
    response_file: "payments/fraud.json"
    status_code: 403

  - function_name: "customer-service"
    priority: 1
    request_match:
      headers:
        X-Customer-Tier: "premium"
    response_file: "customers/premium.json"
    status_code: 200

  - function_name: "customer-service"
    priority: 2
    response_file: "customers/standard.json"
    status_code: 200
YAML

# stubs/orders/success.json
cat > stubs/orders/success.json << 'JSON'
{
  "statusCode": 200,
  "body": {
    "order_id": "{{randomValue type='UUID'}}",
    "customer_id": "{{jsonPath request.body '$.customer_id'}}",
    "status": "CONFIRMED",
    "items": [
      {
        "sku": "PROD-001",
        "quantity": 2,
        "price": 49.99
      }
    ],
    "total_amount": 99.98,
    "currency": "USD",
    "created_at": "{{now}}",
    "estimated_delivery": "{{now offset='3 days'}}",
    "tracking_number": "TRK-{{randomValue type='ALPHANUMERIC' length=10}}",
    "metadata": {
      "processing_time_ms": 245,
      "warehouse": "US-EAST-1"
    }
  }
}
JSON

# stubs/orders/failed.json
cat > stubs/orders/failed.json << 'JSON'
{
  "statusCode": 400,
  "body": {
    "errorType": "ValidationException",
    "errorMessage": "Invalid order data",
    "errors": [
      {
        "field": "items",
        "message": "At least one item is required"
      },
      {
        "field": "customer_id",
        "message": "Customer not found"
      }
    ],
    "timestamp": "{{now}}",
    "request_id": "{{randomValue type='UUID'}}"
  }
}
JSON

# stubs/orders/pending.json
cat > stubs/orders/pending.json << 'JSON'
{
  "statusCode": 202,
  "body": {
    "order_id": "{{randomValue type='UUID'}}",
    "status": "PENDING",
    "message": "Order is being retried",
    "retry_after_seconds": 30,
    "timestamp": "{{now}}"
  }
}
JSON

# stubs/payments/authorized.json
cat > stubs/payments/authorized.json << 'JSON'
{
  "statusCode": 200,
  "body": {
    "transaction_id": "TXN-{{randomValue type='ALPHANUMERIC' length=12}}",
    "status": "AUTHORIZED",
    "amount": "{{jsonPath request.body '$.amount'}}",
    "currency": "{{jsonPath request.body '$.currency'}}",
    "card_last4": "4242",
    "authorization_code": "{{randomValue type='NUMERIC' length=6}}",
    "timestamp": "{{now}}",
    "processor_response": {
      "code": "00",
      "message": "Approved"
    }
  }
}
JSON

# stubs/payments/declined.json
cat > stubs/payments/declined.json << 'JSON'
{
  "statusCode": 402,
  "body": {
    "transaction_id": "TXN-{{randomValue type='ALPHANUMERIC' length=12}}",
    "status": "DECLINED",
    "reason": "Insufficient funds",
    "timestamp": "{{now}}"
  }
}
JSON

# stubs/payments/fraud.json
cat > stubs/payments/fraud.json << 'JSON'
{
  "statusCode": 403,
  "body": {
    "errorType": "FraudDetectedException",
    "errorMessage": "Transaction flagged by fraud detection",
    "fraud_score": 95,
    "reasons": [
      "Unusual transaction pattern",
      "High-risk country",
      "Velocity check failed"
    ],
    "reference_id": "FRAUD-{{randomValue type='ALPHANUMERIC' length=8}}",
    "timestamp": "{{now}}"
  }
}
JSON

# stubs/customers/premium.json
cat > stubs/customers/premium.json << 'JSON'
{
  "statusCode": 200,
  "body": {
    "customer_type": "premium",
    "discount": 0.2,
    "perks": ["priority_support", "fast_shipping"],
    "timestamp": "{{now}}"
  }
}
JSON

# stubs/customers/standard.json
cat > stubs/customers/standard.json << 'JSON'
{
  "statusCode": 200,
  "body": {
    "customer_type": "standard",
    "discount": 0.0,
    "perks": [],
    "timestamp": "{{now}}"
  }
}
JSON

# tests/__init__.py
cat > tests/__init__.py << 'PY'
# tests package
PY

# tests/test_stub_loader.py
cat > tests/test_stub_loader.py << 'PY'
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
PY

echo "Project 'wiremock' created."
