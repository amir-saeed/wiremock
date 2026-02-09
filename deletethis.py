import os, pytest, requests
from wiremock.testing.testcontainer import wiremock_container
from wiremock.constants import Config
from wiremock.client import Mapping, MappingRequest, MappingResponse, HttpMethods, Mappings
from src.lambda_function import lambda_handler

@pytest.fixture(scope="module")
def wm_server():
    with wiremock_container() as wm:
        # This is the line you asked about:
        # We tell the WireMock CLIENT where the admin panel is
        Config.base_url = wm.get_url("__admin")
        
        print(f"\nWireMock started at: {wm.get_base_url()}")
        
        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(method=HttpMethods.GET, url="/data"),
                response=MappingResponse(status=200, body='{"status": "mocked"}')
            )
        )
        yield wm

def test_integration(wm_server):
    # We tell the LAMBDA where the mock server is
    os.environ["EXTERNAL_SERVICE_URL"] = wm_server.get_base_url()
    
    res = lambda_handler({}, None)
    assert res["statusCode"] == 200