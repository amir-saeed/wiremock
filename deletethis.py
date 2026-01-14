import json
import requests

def lambda_handler(event, context):
    # Parse API Gateway event
    if 'httpMethod' in event and event['httpMethod'] == 'GET':
        try:
            # Example: Call an external API (we'll mock this)
            response = requests.get('https://api.example.com/weather?city=London')
            data = response.json()
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Weather data', 'data': data})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid method'})
        }