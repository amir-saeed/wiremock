import json
from unittest.mock import patch
from src.lambda_function import lambda_handler

def test_lambda_handler_success():
    event = {'httpMethod': 'GET'}
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {'temp': 20}
        mock_get.return_value.status_code = 200
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        assert 'Weather data' in json.loads(response['body'])['message']

def test_lambda_handler_failure():
    event = {'httpMethod': 'POST'}
    response = lambda_handler(event, None)
    assert response['statusCode'] == 400
    assert 'Invalid method' in json.loads(response['body'])['error']