import os
import json
import pytest
from wiremock.testing.testcontainer import wiremock_container
from wiremock.sdk import Mapping, HttpMethods, MappingRequest, MappingResponse, WireMockClient
from src.lambda_function import lambda_handler

@pytest.fixture(scope="module")
def wm_server():
    # Spin up WireMock container
    with wiremock_container() as wm:
        # Get the internal URL of the container
        base_url = wm.get_url("__admin")
        # Create a client instance instead of using global Config
        client = WireMockClient(base_url=base_url)
        
        # Setup a stub
        client.mappings.create_mapping(
            Mapping(
                request=MappingRequest(method=HttpMethods.GET, url="/data"),
                response=MappingResponse(
                    status=200, 
                    body=json.dumps({"id": "wiremock-1", "value": "real-integration"}),
                    headers={"Content-Type": "application/json"}
                )
            )
        )
        # Yield the container object so we can access its host/port
        yield wm

def test_lambda_integration_with_wiremock(wm_server):
    # Inject the actual host:port of the container into the environment
    os.environ["EXTERNAL_SERVICE_URL"] = wm_server.get_base_url()
    
    event = {} # Mock API Gateway event
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["data"]["id"] == "wiremock-1"