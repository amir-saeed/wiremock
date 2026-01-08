from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class LambdaInvocation:
    function_name: str
    payload: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None
