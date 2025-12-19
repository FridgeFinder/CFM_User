"""
Utility functions for API responses and JWT handling
"""
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any

# Use root logger (same as Lambda handler) since all logs go to same CloudWatch stream
logger = logging.getLogger()


class ErrorCode(str, Enum):
    """Centralized error codes for API responses"""
    USER_ID_REQUIRED = "USER_ID_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    EMPTY_REQUEST_BODY = "EMPTY_REQUEST_BODY"
    INVALID_JSON = "INVALID_JSON"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


def get_authenticated_user_id(event: Dict[str, Any]) -> str:
    """
    Extract userId from JWT token claims
    API Gateway v2 (HTTP API) provides JWT claims in requestContext.authorizer.jwt.claims
    Args:
        event: API Gateway HTTP API event
    Returns:
        User ID from JWT 'sub' claim
    """
    # For HTTP API, JWT claims are in requestContext.authorizer.jwt.claims
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')

    return user_id


def response(status_code: int, body: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Helper function to create properly formatted API Gateway response
    
    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)
        request_id: Optional request ID to include in response headers
        
    Returns:
        API Gateway response dict
    """
    headers = {
        'Content-Type': 'application/json'
    }
    if request_id:
        headers['X-Request-Id'] = request_id
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }


def error_response(status_code: int, error_code: ErrorCode, message: str, field: Optional[str] = None, 
                   log_level: Optional[str] = None, request_id: Optional[str] = None, 
                   extra: Optional[Dict[str, Any]] = None):
    """
    Create standardized error response with optional logging
    
    Args:
        status_code: HTTP status code
        error_code: Error code from ErrorCode enum
        message: Human-readable error message
        field: Optional field name for validation errors
        log_level: Optional log level ('warning', 'error', 'info'). If provided, will log with structured context.
        request_id: Optional request ID to include in response headers and logging
        extra: Optional dictionary of additional context for structured logging (e.g., {'user_id': '123', 'operation': 'create_user'})
    
    Returns:
        Formatted API Gateway response with error details
    """
    error_body = {
        'code': error_code.value,
        'message': message
    }
    if field:
        error_body['field'] = field
    
    # Optional structured logging
    if log_level:
        log_func = getattr(logger, log_level.lower(), logger.info)
        log_context = extra.copy() if extra else {}
        log_context['error_code'] = error_code.value
        log_context['status_code'] = status_code
        if request_id:
            log_context['request_id'] = request_id
        log_func(message, extra=log_context)
    
    return response(status_code, {'error': error_body}, request_id)

