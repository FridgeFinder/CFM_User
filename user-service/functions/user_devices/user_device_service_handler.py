"""
Lambda handler for User Device Service.
Handles user device registration routes, auth checks, and validation.
"""
import os
import json
import logging
from typing import Dict, Any, Tuple, Optional

from utils import get_authenticated_user_id
from http_utils import HttpStatus, error_response, ErrorCode
from dynamo_utils import get_ddb_client
from user_device_repository import UserDeviceRepository
from user_device_service import UserDeviceService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


dynamodb_client = get_ddb_client()
user_devices_table_name = os.environ['USER_DEVICES_TABLE']
user_device_repository = UserDeviceRepository(dynamodb_client, user_devices_table_name)
user_device_service = UserDeviceService(user_device_repository)


def get_user_id_from_path(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    path_params = event.get('pathParameters', {})
    user_id = path_params.get('userId')
    if not user_id:
        return None, error_response(HttpStatus.BAD_REQUEST, ErrorCode.USER_ID_REQUIRED, 'userId is required in path')
    return user_id, None


def get_installation_id_from_path(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    path_params = event.get('pathParameters', {})
    installation_id = path_params.get('installationId')
    if not installation_id:
        return None, error_response(
            HttpStatus.BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            'installationId is required in path',
            field='installationId',
        )
    return installation_id, None


def check_self_access_authorization(
    user_id: str,
    authenticated_user_id: str,
    operation: str,
    request_id: str,
) -> Optional[Dict[str, Any]]:
    if user_id != authenticated_user_id:
        logger.warning(
            'Authorization denied',
            extra={
                'operation': operation,
                'requested_user_id': user_id,
                'authenticated_user_id': authenticated_user_id,
                'request_id': request_id,
            },
        )
        return error_response(
            HttpStatus.FORBIDDEN,
            ErrorCode.FORBIDDEN,
            f'User can only {operation} their own user data',
            request_id=request_id,
        )
    return None


def parse_json_body(event: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    try:
        body = event.get('body', '{}')
        if body is None:
            return {}, None
        if not isinstance(body, str):
            return None, error_response(HttpStatus.BAD_REQUEST, ErrorCode.INVALID_JSON, 'Invalid JSON in request body')
        return json.loads(body), None
    except (json.JSONDecodeError, TypeError):
        return None, error_response(HttpStatus.BAD_REQUEST, ErrorCode.INVALID_JSON, 'Invalid JSON in request body')


def handle_post_user_device(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    user_id, error = get_user_id_from_path(event)
    if error:
        return error

    installation_id, error = get_installation_id_from_path(event)
    if error:
        return error

    body, error = parse_json_body(event)
    if error:
        return error

    auth_error = check_self_access_authorization(user_id, authenticated_user_id, 'register user device for', request_id)
    if auth_error:
        return auth_error

    token = body.get('token')
    if not token:
        return error_response(
            HttpStatus.BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            'token is required in request body',
            field='token',
            request_id=request_id,
        )

    platform = body.get('platform')
    return user_device_service.register_device(
        user_id=user_id,
        installation_id=installation_id,
        token=token,
        platform=platform,
        request_id=request_id,
    )


def handle_get_user_device(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    user_id, error = get_user_id_from_path(event)
    if error:
        return error

    installation_id, error = get_installation_id_from_path(event)
    if error:
        return error

    auth_error = check_self_access_authorization(user_id, authenticated_user_id, 'access user devices for', request_id)
    if auth_error:
        return auth_error

    return user_device_service.get_device(
        user_id=user_id,
        installation_id=installation_id,
        request_id=request_id,
    )


def handle_patch_user_device(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    user_id, error = get_user_id_from_path(event)
    if error:
        return error

    installation_id, error = get_installation_id_from_path(event)
    if error:
        return error

    body, error = parse_json_body(event)
    if error:
        return error

    auth_error = check_self_access_authorization(user_id, authenticated_user_id, 'update user device for', request_id)
    if auth_error:
        return auth_error

    return user_device_service.update_device(
        user_id=user_id,
        installation_id=installation_id,
        updates=body,
        request_id=request_id,
    )


def handle_delete_user_device(event: Dict[str, Any], authenticated_user_id: str, request_id: str) -> Dict[str, Any]:
    user_id, error = get_user_id_from_path(event)
    if error:
        return error

    installation_id, error = get_installation_id_from_path(event)
    if error:
        return error

    auth_error = check_self_access_authorization(user_id, authenticated_user_id, 'unregister user device for', request_id)
    if auth_error:
        return auth_error

    return user_device_service.unregister_device(
        user_id=user_id,
        installation_id=installation_id,
        request_id=request_id,
    )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    request_id = context.aws_request_id if context else 'unknown'
    http_method = event.get('requestContext', {}).get('http', {}).get('method')
    path = event.get('rawPath', 'unknown')
    authenticated_user_id = get_authenticated_user_id(event)

    logger.info(
        'Request received',
        extra={
            'request_id': request_id,
            'http_method': http_method,
            'path': path,
            'authenticated_user_id': authenticated_user_id,
        },
    )

    if not authenticated_user_id:
        logger.error(
            'Authentication failed: No sub found in JWT',
            extra={'request_id': request_id, 'path': path},
        )
        return error_response(
            HttpStatus.INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            'Authentication failed: No sub found in JWT',
            request_id=request_id,
        )

    try:
        if http_method == 'GET':
            result = handle_get_user_device(event, authenticated_user_id, request_id)
        elif http_method == 'PATCH':
            result = handle_patch_user_device(event, authenticated_user_id, request_id)
        elif http_method == 'POST':
            result = handle_post_user_device(event, authenticated_user_id, request_id)
        elif http_method == 'DELETE':
            result = handle_delete_user_device(event, authenticated_user_id, request_id)
        else:
            logger.error(
                'Invalid http_method',
                extra={'http_method': http_method, 'path': path, 'request_id': request_id},
            )
            return error_response(
                HttpStatus.INTERNAL_SERVER_ERROR,
                ErrorCode.INTERNAL_SERVER_ERROR,
                'Invalid http_method',
                request_id=request_id,
            )

        logger.info(
            'Request completed',
            extra={
                'request_id': request_id,
                'http_method': http_method,
                'path': path,
                'status_code': result.get('statusCode'),
                'user_id': authenticated_user_id,
            },
        )
        return result

    except Exception as e:
        logger.exception(
            'Unexpected error in lambda_handler',
            extra={
                'request_id': request_id,
                'http_method': http_method,
                'path': path,
                'user_id': authenticated_user_id,
                'error_message': str(e),
                'error_type': type(e).__name__,
            },
        )
        return error_response(HttpStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_SERVER_ERROR, 'An unexpected error occurred')
