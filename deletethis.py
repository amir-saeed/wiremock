import os
import json
import pytest
from wiremock.testing.testcontainer import wiremock_container
from wiremock.client import Mapping, MappingRequest, MappingResponse, HttpMethods, Config, Mappings
from src.lambda_function import lambda_handler

@pytest.fixture(scope="module")
def wm_server():
    # Spin up WireMock container
    with wiremock_container(secure=False) as wm:
        # Configure the WireMock Python client to talk to this container
        Config.base_url = wm.get_url("__admin")
        
        # Setup a stub: When GET /data is called, return 200 with JSON
        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(method=HttpMethods.GET, url="/data"),
                response=MappingResponse(
                    status=200, 
                    body=json.dumps({"id": "wiremock-1", "value": "real-integration"}),
                    headers={"Content-Type": "application/json"}
                )
            )
        )
        yield wm

def test_lambda_integration_with_wiremock(wm_server):
    # Inject the WireMock URL into the environment so the Lambda knows where to call
    os.environ["EXTERNAL_SERVICE_URL"] = wm_server.get_base_url()
    
    event = {} # Mock API Gateway event
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["data"]["id"] == "wiremock-1"