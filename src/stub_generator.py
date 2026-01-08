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
