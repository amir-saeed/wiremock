import os
import json
import pytest
import requests
from wiremock.testing.testcontainer import wiremock_container
from wiremock.constants import Config
from wiremock.client import Mapping, MappingRequest, MappingResponse, HttpMethods, Mappings
from src.lambda_function import lambda_handler

@pytest.fixture(scope="module")
def wm_server():
    # 1. Start WireMock container
    with wiremock_container(secure=False) as wm:
        # 2. Configure the global WireMock client to talk to the container
        # Note: Config is imported from wiremock.constants
        Config.base_url = wm.get_url("__admin")
        
        # 3. Create a mock mapping (stub)
        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(method=HttpMethods.GET, url="/data"),
                response=MappingResponse(
                    status=200, 
                    body=json.dumps({"id": "wiremock-1", "value": "real-integration"}),
                    headers={"Content-Type": "application/json"}
                ),
                persistent=False
            )
        )
        yield wm

def test_lambda_integration_with_wiremock(wm_server):
    # Pass the container's dynamic URL to the Lambda function logic
    os.environ["EXTERNAL_SERVICE_URL"] = wm_server.get_base_url()
    
    # Simulate API Gateway event
    event = {"requestContext": {"stage": "test"}} 
    response = lambda_handler(event, None)
    
    # Assertions
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["data"]["id"] == "wiremock-1"