"""
Lambda handler for Username Availability Check
Standalone public endpoint for checking username availability
"""
import boto3
import os
import json
import logging
from typing import Dict, Any

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_ddb_client() -> boto3.client:
    """
    Get DynamoDB client with support for local testing
    Set DEPLOYMENT_TARGET=local to connect to LocalStack
    """
    deployment_target = os.getenv("DEPLOYMENT_TARGET", "local")
    if deployment_target == "aws":
        return boto3.client("dynamodb")
    else:
        return boto3.client(
            "dynamodb",
            endpoint_url="http://localstack:4566"
        )

# Initialize DynamoDB client
dynamodb_client = get_ddb_client()
table_name = os.environ['USERS_TABLE']


def response(status_code: int, body: Dict[str, Any], request_id: str = None) -> Dict[str, Any]:
    """Build API Gateway response"""
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }
    if request_id:
        headers['X-Request-Id'] = request_id
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }


def is_username_available(username: str) -> bool:
    """
    Check if a username is available (not taken)
    
    Args:
        username: The username to check
        request_id: Optional request ID for tracing
        
    Returns:
        True if username is available, False if taken
        
    Raises:
        Exception: If DynamoDB query fails
    """
    result = dynamodb_client.query(
        TableName=table_name,
        IndexName='username-index',
        KeyConditionExpression='username = :username',
        ExpressionAttributeValues={
            ':username': {'S': username}
        },
        Limit=1,
        Select='COUNT'
    )
    return result.get('Count', 0) == 0


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for username availability check
    GET /v1/users/check-username/{username}
    """
    request_id = context.aws_request_id if context else 'unknown'
    # Extract username from path
    path_params = event.get('pathParameters', {})
    username = path_params.get('username')
    
    # Check availability
    try:
        is_available = is_username_available(username)
        return response(200, {'available': is_available}, request_id)
    except Exception as e:
        logger.exception('Error checking username availability',
                        extra={'username': username,
                               'request_id': request_id,
                               'error_message': str(e),
                               'error_type': type(e).__name__})
        return response(500, {'error': 'An error occurred checking username availability, try again'}, request_id)
