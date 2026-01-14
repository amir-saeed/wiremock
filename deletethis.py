import json
import os
import requests

def lambda_handler(event, context):
    # Retrieve external service URL from env (injected during testing or via Terraform)
    external_url = os.getenv("EXTERNAL_SERVICE_URL", "https://api.example.com")
    
    # Simple logic: Call external API
    try:
        response = requests.get(f"{external_url}/data")
        response.raise_for_status()
        data = response.json()
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Success", "data": data})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }