"""
Internal Lambda handler for service-to-service user queries.
Authentication: IAM (SigV4) - no Firebase JWT required.
Returns a projected subset of user data (email, fcmToken, settings).
"""
import os
import logging
from typing import Any, Dict, Optional
from http_utils import HttpStatus, ErrorCode, http_response, error_response
from dynamo_utils import get_ddb_client

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


dynamodb = get_ddb_client()
USERS_TABLE = os.environ["USERS_TABLE"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dynamodb_to_dict(item: Dict) -> Dict:
    """Flatten DynamoDB typed attribute map to a plain dict."""
    result = {}
    for key, value in item.items():
        type_key, typed_value = next(iter(value.items()))
        if type_key == "S":
            result[key] = typed_value
        elif type_key == "N":
            result[key] = int(typed_value)
        elif type_key == "BOOL":
            result[key] = typed_value
        elif type_key == "M":
            result[key] = _dynamodb_to_dict(typed_value)
        elif type_key == "L":
            result[key] = [_dynamodb_to_dict(v) if "M" in v else next(iter(v.values())) for v in typed_value]
        elif type_key == "NULL":
            result[key] = None
        else:
            result[key] = typed_value
    return result


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

def get_user_details(user_id: str, logger: logging.LoggerAdapter) -> Optional[Dict]:
    """Fetch email, fcmToken, and settings from the users table."""
    logger.info("Fetching user details", extra={"user_id": user_id})

    resp = dynamodb.get_item(
        TableName=USERS_TABLE,
        Key={"userId": {"S": user_id}},
        ProjectionExpression="email, fcmToken, settings",
    )

    if "Item" not in resp:
        # User may have just been deleted — caller should handle None gracefully
        logger.warning("User not found", extra={"user_id": user_id})
        return None

    return _dynamodb_to_dict(resp["Item"])


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event: Dict, context: Any) -> Dict:
    request_id = context.aws_request_id if context else "unknown"
    logger = logging.LoggerAdapter(_logger, {"request_id": request_id})
    http_method = event.get("requestContext", {}).get("http", {}).get("method")

    logger.info("Internal request received", extra={"http_method": http_method})

    if http_method != "GET":
        return error_response(HttpStatus.METHOD_NOT_ALLOWED, ErrorCode.METHOD_NOT_ALLOWED, f"Method {http_method} not allowed", request_id=request_id)

    user_id = (event.get("pathParameters") or {}).get("userId")
    if not user_id:
        return error_response(HttpStatus.BAD_REQUEST, ErrorCode.USER_ID_REQUIRED, "userId is required in path", request_id=request_id)

    try:
        user = get_user_details(user_id, logger)
    except Exception as e:
        logger.error("Error fetching user details", extra={"user_id": user_id, "error": str(e)})
        return error_response(HttpStatus.INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL_SERVER_ERROR, "Internal server error", request_id=request_id)

    if user is None:
        return error_response(HttpStatus.NOT_FOUND, ErrorCode.ITEM_NOT_FOUND, "User not found", request_id=request_id)

    logger.info("Internal request completed", extra={"user_id": user_id})
    return http_response(HttpStatus.OK, {"user": user}, request_id)
