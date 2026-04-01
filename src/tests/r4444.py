from pydantic import BaseModel, ConfigDict, ValidationError

class UserProfile(BaseModel):
    model_config = ConfigDict(extra='forbid')  # This blocks extra fields
    username: str
    age: int

# Example: Input contains 'admin_status' which isn't in the schema
payload = {"username": "jdoe", "age": 30, "admin_status": True}

try:
    user = UserProfile(**payload)
except ValidationError as e:
    print(f"Caught extra field: {e.errors()[0]['loc']}")



from pydantic import BaseModel
from typing import Optional

class APIResponse(BaseModel):
    id: int               # Required
    status: str           # Required
    metadata: Optional[dict] = None  # Explicitly optional

# This will fail because 'status' is missing
try:
    data = APIResponse(id=101)
except Exception as e:
    print("Failed: Missing required field 'status'")