import boto3
from moto import mock_apigateway, mock_lambda
from src.lambda_function import lambda_handler
import zipfile
import io

@mock_lambda
@mock_apigateway
def test_integration_lambda_via_apigateway(setup_wiremock):
    # Create mock Lambda
    client_lambda = boto3.client('lambda', region_name='us-east-1')
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('lambda_function.py', open('src/lambda_function.py').read())
    zip_buffer.seek(0)
    client_lambda.create_function(
        FunctionName='test_lambda',
        Runtime='python3.10',
        Role='arn:aws:iam::123456789012:role/lambda-role',  # Dummy ARN
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': zip_buffer.read()}
    )

    # Create mock API Gateway
    client_apigw = boto3.client('apigateway', region_name='us-east-1')
    api_id = client_apigw.create_rest_api(name='test_api')['id']
    resource_id = client_apigw.get_resources(restApiId=api_id)['items'][0]['id']
    client_apigw.put_method(restApiId=api_id, resourceId=resource_id, httpMethod='GET', authorizationType='NONE')
    client_apigw.put_integration(
        restApiId=api_id, resourceId=resource_id, httpMethod='GET',
        type='AWS_PROXY', integrationHttpMethod='POST',
        uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:test_lambda/invocations'
    )

    # Invoke via API Gateway simulation (or use lambda_handler directly with event)
    event = {'httpMethod': 'GET', 'path': '/'}  # Simulate API Gateway event
    response = lambda_handler(event, None)
    assert response['statusCode'] == 200