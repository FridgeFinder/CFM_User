"""Public Lambda handler for retrieving a username by user ID."""
import logging
import os
from typing import Any, Dict, Optional

from dynamo_utils import get_ddb_client
from http_utils import ErrorCode, HttpStatus, error_response, http_response


logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_client = get_ddb_client()
table_name = os.environ['USERS_TABLE']


def get_username(user_id: str) -> Optional[str]:
    """Fetch only the username for a user ID."""
    result = dynamodb_client.get_item(
        TableName=table_name,
        Key={'userId': {'S': user_id}},
        ProjectionExpression='username',
    )
    item = result.get('Item')
    if not item or 'username' not in item:
        return None
    return item['username'].get('S')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle GET /v1/users/{userId}/username without authentication."""
    request_id = context.aws_request_id if context else 'unknown'
    path_params = event.get('pathParameters') or {}
    user_id = path_params.get('userId')
    if not user_id:
        return error_response(
            HttpStatus.BAD_REQUEST,
            ErrorCode.USER_ID_REQUIRED,
            'userId is required in path',
            request_id=request_id,
        )

    try:
        username = get_username(user_id)
    except Exception:
        logger.exception('Error fetching username', extra={'user_id': user_id, 'request_id': request_id})
        return error_response(
            HttpStatus.INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            'Internal server error',
            request_id=request_id,
        )

    if username is None:
        return error_response(
            HttpStatus.NOT_FOUND,
            ErrorCode.ITEM_NOT_FOUND,
            'User or username not found',
            request_id=request_id,
        )

    return http_response(HttpStatus.OK, {'username': username}, request_id)