import json

def lambda_handler(event, context):
    """Sample Lambda function"""
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello user service",
        }),
    }
