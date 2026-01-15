import os
import json
import pytest
import requests
import time
from wiremock.testing.testcontainer import wiremock_container
from wiremock.constants import Config
from wiremock.client import Mapping, MappingRequest, MappingResponse, HttpMethods, Mappings
from src.lambda_function import lambda_handler

@pytest.fixture(scope="module")
def wm_server():
    # Use the context manager to spin up WireMock
    with wiremock_container(secure=False) as wm:
        # Wait a moment for the internal server to be fully ready
        # Even if the container is 'started', the Java app inside might be booting
        base_url = wm.get_base_url()
        admin_url = wm.get_url("__admin")
        
        # Configure global client
        Config.base_url = admin_url
        
        # Simple health check retry
        for _ in range(10):
            try:
                if requests.get(admin_url + "/mappings").status_code == 200:
                    break
            except:
                time.sleep(1)

        # Create the mock
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
    # Set the environment variable to the dynamic container URL
    os.environ["EXTERNAL_SERVICE_URL"] = wm_server.get_base_url()
    
    event = {}
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["data"]["id"] == "wiremock-1"