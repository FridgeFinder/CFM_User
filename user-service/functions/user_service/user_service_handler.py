"""
Lambda handler for User Service
Handles HTTP event parsing, JWT extraction, routing, and error handling
"""
import os
import json
import logging
from typing import Dict, Any, Tuple, Optional
from utils import get_authenticated_user_id
from http_utils import HttpStatus, error_response, ErrorCode
from dynamo_utils import get_ddb_client
from repository import UserRepository
from service import UserService

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Initialize DynamoDB client, repository, and service
dynamodb_client = get_ddb_client()
table_name = os.environ['USERS_TABLE']
user_repository = UserRepository(dynamodb_client, table_name)
user_service = UserService(user_repository)


def get_user_id_from_path(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Extract userId from path parameters
    
    Args:
        event: API Gateway HTTP API event
        
    Returns:
        Tuple of (user_id, error_response) - one will be None
    """
    path_params = event.get('pathParameters', {})
    user_id = path_params.get('userId')
    
    if not user_id:
        return None, error_response(HttpStatus.BAD_REQUEST, ErrorCode.USER_ID_REQUIRED, 'userId is required in path')
    
    return user_id, None


def check_self_access_authorization(
    user_id: str, 
    authenticated_user_id: str, 
    operation: str, 
    request_id: str
) -> Optional[Dict[str, Any]]:
    """
    Check if user is authorized to access/modify their own resource
    
    Args:
        user_id: Target user ID from path/body
        authenticated_user_id: Authenticated user ID from JWT
        operation: Operation being performed
        request_id: Request ID for tracing
        
    Returns:
        error_response if unauthorized, None if authorized
    """
    if user_id != authenticated_user_id:
        logger.warning(
            'Authorization denied',
            extra={'operation': operation,
                   'requested_user_id': user_id,
                   'authenticated_user_id': authenticated_user_id,
                   'request_id': request_id})
        return error_response(
            HttpStatus.FORBIDDEN,
            ErrorCode.FORBIDDEN,
            f'User can only {operation} their own user data',
            request_id=request_id)
    return None


def parse_json_body(event: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Parse JSON body from event
    
    Args:
        event: API Gateway HTTP API event
        
    Returns:
        Tuple of (parsed_body, error_response) - one will be None
    """
    try:
        return json.loads(event.get('body', '{}')), None
    except json.JSONDecodeError:
        return None, error_response(HttpStatus.BAD_REQUEST, ErrorCode.INVALID_JSON, 'Invalid JSON in request body')


def handle_post_user(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    """Handle POST /v1/users - Create user"""
    body, error = parse_json_body(event)
    if error:
        return error
    
    requested_user_id = body.get('userId')
    if not requested_user_id:
        return error_response(HttpStatus.BAD_REQUEST, ErrorCode.USER_ID_REQUIRED, 'userId is required in request body', 
                            field='userId', request_id=request_id)
    
    # Authorization: user can only create their own profile
    auth_error = check_self_access_authorization(requested_user_id, authenticated_user_id, 'create', request_id)
    if auth_error:
        return auth_error
    
    return user_service.create_user(body, request_id)


def handle_get_user(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    """Handle GET /v1/users/{userId} - Get user"""
    user_id, error = get_user_id_from_path(event)
    if error:
        return error
    
    # Authorization: user can only access their own data
    auth_error = check_self_access_authorization(user_id, authenticated_user_id, 'access', request_id)
    if auth_error:
        return auth_error
    
    return user_service.get_user(user_id, request_id)


def handle_patch_user(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    """Handle PATCH /v1/users/{userId} - Update user"""
    user_id, error = get_user_id_from_path(event)
    if error:
        return error
    
    body, error = parse_json_body(event)
    if error:
        return error
    
    # Authorization: user can only update their own profile
    auth_error = check_self_access_authorization(user_id, authenticated_user_id, 'update', request_id)
    if auth_error:
        return auth_error

    return user_service.update_user(user_id, body, request_id)


def handle_delete_user(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    """Handle DELETE /v1/users/{userId} - Delete user"""
    user_id, error = get_user_id_from_path(event)
    if error:
        return error
    
    # Authorization: user can only delete their own profile
    auth_error = check_self_access_authorization(user_id, authenticated_user_id, 'delete', request_id)
    if auth_error:
        return auth_error
    
    return user_service.delete_user(user_id, request_id)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler - routes requests to appropriate API functions
    
    Responsibilities:
    - Parse HTTP event (method, path)
    - Extract and validate JWT authentication
    - Route to handler functions
    - Handle unexpected errors
    """
    request_id = context.aws_request_id if context else 'unknown'
    http_method = event.get("requestContext", {}).get("http", {}).get("method")
    path = event.get("rawPath", "unknown")
    authenticated_user_id = get_authenticated_user_id(event)
    # Log incoming request with structured fields
    logger.info(
        'Request received',
        extra={
            'request_id': request_id,
            'http_method': http_method,
            'path': path,
            'authenticated_user_id': authenticated_user_id
            }
        )
    
    if not authenticated_user_id:
        # Should never get here if API Gateway JWT authorizer is configured correctly
        logger.error(
            'Authentication failed: No sub found in JWT',
            extra={'request_id': request_id, 'path': path})
        return error_response(
            HttpStatus.INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            'Authentication failed: No sub found in JWT',
            request_id=request_id)
    # Route to appropriate handler function
    try:        
        if http_method == 'GET':
            result = handle_get_user(event, authenticated_user_id, request_id)
        elif http_method == 'POST':
            result = handle_post_user(event, authenticated_user_id, request_id)
        elif http_method == 'PATCH':
            result = handle_patch_user(event, authenticated_user_id, request_id)
        elif http_method == 'DELETE':
            result = handle_delete_user(event, authenticated_user_id, request_id)
        else:
            # Should never get here - indicates a configuration error
            logger.error(
                'Invalid http_method',
                extra={'http_method': http_method, 'path': path, 'request_id': request_id})
            return error_response(
                HttpStatus.INTERNAL_SERVER_ERROR,
                ErrorCode.INTERNAL_SERVER_ERROR,
                'Invalid http_method',
                request_id=request_id)
        
        # Log successful completion
        logger.info('Request completed',
                   extra={'request_id': request_id,
                          'http_method': http_method,
                          'path': path,
                          'status_code': result.get('statusCode'),
                          'user_id': authenticated_user_id})
        return result
            
    except Exception as e:
        logger.exception('Unexpected error in lambda_handler',
                        extra={'request_id': request_id,
                               'http_method': http_method,
                               'path': path,
                               'user_id': authenticated_user_id,
                               'error_message': str(e),
                               "error_type": type(e).__name__})
        return error_response(HttpStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_SERVER_ERROR, 'An unexpected error occurred')

