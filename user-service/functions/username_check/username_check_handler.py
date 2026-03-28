"""
Lambda handler for Username Availability Check
Standalone public endpoint for checking username availability
"""
import os
import logging
from typing import Dict, Any
from http_utils import HttpStatus, ErrorCode, http_response, error_response
from dynamo_utils import get_ddb_client
from validation_utils import validate_username

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Initialize DynamoDB client
dynamodb_client = get_ddb_client()
table_name = os.environ['USERS_TABLE']


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

    # Validate username format before querying
    if not username:
        return error_response(HttpStatus.BAD_REQUEST, ErrorCode.VALIDATION_ERROR, 'Username is required', request_id=request_id)
    try:
        validate_username(username)
    except ValueError as e:
        return error_response(HttpStatus.BAD_REQUEST, ErrorCode.VALIDATION_ERROR, str(e), request_id=request_id)

    # Check availability
    try:
        is_available = is_username_available(username)
        return http_response(HttpStatus.OK, {'available': is_available}, request_id)
    except Exception as e:
        logger.exception('Error checking username availability',
                        extra={'username': username,
                               'request_id': request_id,
                               'error_message': str(e),
                               'error_type': type(e).__name__})
        return error_response(HttpStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_SERVER_ERROR, 'An error occurred checking username availability, try again', request_id=request_id)
