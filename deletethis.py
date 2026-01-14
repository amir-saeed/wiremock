import json
from src.lambda_function import lambda_handler

def test_lambda_handler_success(mocker):
    # Mock the external HTTP call
    mock_get = mocker.patch('src.lambda_function.requests.get')
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"id": 123, "status": "active"}

    # Simulate API Gateway Event
    event = {"httpMethod": "GET", "path": "/test"}
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["data"]["id"] == 123