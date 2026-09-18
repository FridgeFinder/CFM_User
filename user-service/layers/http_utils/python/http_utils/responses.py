import json
from typing import Any, Dict, Optional
from .codes import ErrorCode


def http_response(status_code: int, body: Any, request_id: Optional[str] = None) -> Dict:
    """Build a standard API Gateway HTTP response."""
    headers = {"Content-Type": "application/json"}
    if request_id:
        headers["X-Request-Id"] = request_id
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }


def error_response(
    status_code: int,
    error_code: ErrorCode,
    message: str,
    field: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict:
    """Build a structured error response: {"error": {"code": ..., "message": ..., "field": ...}}."""
    error_body: Dict[str, Any] = {
        "code": error_code.value,
        "message": message,
    }
    if field:
        error_body["field"] = field
    return http_response(status_code, {"error": error_body}, request_id)
