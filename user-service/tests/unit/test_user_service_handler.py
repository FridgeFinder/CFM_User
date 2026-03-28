"""
Unit tests for functions/user_service/app.py (Lambda handler)
Covers: lambda_handler routing, helper functions, authorization.
The module-level UserService singleton is patched per test.
"""
import json
from unittest.mock import MagicMock, patch
from http_utils import HttpStatus
import user_service_handler as app


# ── fixtures ───────────────────────────────────────────────────────────────

def _make_context(request_id: str = "req-test"):
    ctx = MagicMock()
    ctx.aws_request_id = request_id
    return ctx


def _make_event(
    method: str = "GET",
    path: str = "/v1/users/u-1",
    user_id_path: str = "u-1",
    auth_user_id: str = "u-1",
    body: dict = None,
) -> dict:
    event = {
        "requestContext": {
            "http": {"method": method},
            "authorizer": {"jwt": {"claims": {"sub": auth_user_id}}},
        },
        "rawPath": path,
        "pathParameters": {"userId": user_id_path},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


def _ok_response(data: dict = None) -> dict:
    """Build a fake 200 service response."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data or {"user": {"userId": "u-1"}}),
    }


# ── get_user_id_from_path ──────────────────────────────────────────────────

class TestGetUserIdFromPath:
    def test_returns_user_id_when_present(self):
        event = {"pathParameters": {"userId": "u-abc"}}
        user_id, error = app.get_user_id_from_path(event)
        assert user_id == "u-abc"
        assert error is None

    def test_returns_error_when_missing(self):
        event = {"pathParameters": {}}
        user_id, error = app.get_user_id_from_path(event)
        assert user_id is None
        assert error is not None
        assert error["statusCode"] == HttpStatus.BAD_REQUEST

    def test_returns_error_when_no_path_params(self):
        event = {}
        user_id, error = app.get_user_id_from_path(event)
        assert user_id is None
        assert error is not None


# ── check_self_access_authorization ───────────────────────────────────────

class TestCheckSelfAccessAuthorization:
    def test_returns_none_when_ids_match(self):
        result = app.check_self_access_authorization("u-1", "u-1", "access", "req-1")
        assert result is None

    def test_returns_403_when_ids_differ(self):
        result = app.check_self_access_authorization("u-1", "u-2", "access", "req-1")
        assert result is not None
        assert result["statusCode"] == HttpStatus.FORBIDDEN
        body = json.loads(result["body"])
        assert body["error"]["code"] == "FORBIDDEN"


# ── parse_json_body ────────────────────────────────────────────────────────

class TestParseJsonBody:
    def test_parses_valid_json(self):
        event = {"body": '{"key": "value"}'}
        body, error = app.parse_json_body(event)
        assert body == {"key": "value"}
        assert error is None

    def test_returns_empty_dict_when_no_body(self):
        body, error = app.parse_json_body({})
        assert body == {}
        assert error is None

    def test_returns_error_on_invalid_json(self):
        event = {"body": "not json {"}
        body, error = app.parse_json_body(event)
        assert body is None
        assert error is not None
        assert error["statusCode"] == HttpStatus.BAD_REQUEST
        body_parsed = json.loads(error["body"])
        assert body_parsed["error"]["code"] == "INVALID_JSON"


# ── lambda_handler routing ─────────────────────────────────────────────────

class TestLambdaHandlerRouting:
    def test_get_request_routes_to_get_handler(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.get_user.return_value = _ok_response()
            result = app.lambda_handler(_make_event("GET"), _make_context())
        mock_svc.get_user.assert_called_once()
        assert result["statusCode"] == 200

    def test_post_request_routes_to_post_handler(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.create_user.return_value = {
                "statusCode": 201,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"user": {"userId": "u-1"}}),
            }
            result = app.lambda_handler(
                _make_event("POST", body={"userId": "u-1"}), _make_context()
            )
        mock_svc.create_user.assert_called_once()
        assert result["statusCode"] == 201

    def test_patch_request_routes_to_patch_handler(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.update_user.return_value = _ok_response()
            result = app.lambda_handler(
                _make_event("PATCH", body={"email": "e@e.com"}), _make_context()
            )
        mock_svc.update_user.assert_called_once()
        assert result["statusCode"] == 200

    def test_delete_request_routes_to_delete_handler(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.delete_user.return_value = {
                "statusCode": 204,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(None),
            }
            result = app.lambda_handler(_make_event("DELETE"), _make_context())
        mock_svc.delete_user.assert_called_once()
        assert result["statusCode"] == 204

    def test_unknown_method_returns_500(self):
        # user_service/app.py returns 500 (INTERNAL_SERVER_ERROR) for unrecognised methods
        result = app.lambda_handler(_make_event("OPTIONS"), _make_context())
        assert result["statusCode"] == HttpStatus.INTERNAL_SERVER_ERROR

    def test_missing_auth_returns_500(self):
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "rawPath": "/v1/users/u-1",
            "pathParameters": {"userId": "u-1"},
        }
        result = app.lambda_handler(event, _make_context())
        assert result["statusCode"] == HttpStatus.INTERNAL_SERVER_ERROR

    def test_unexpected_exception_returns_500(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.get_user.side_effect = RuntimeError("unexpected boom")
            result = app.lambda_handler(_make_event("GET"), _make_context())
        assert result["statusCode"] == HttpStatus.INTERNAL_SERVER_ERROR


# ── handle_get_user ────────────────────────────────────────────────────────

class TestHandleGetUser:
    def test_returns_error_when_user_id_missing(self):
        event = {"requestContext": {"http": {"method": "GET"}}, "pathParameters": {}}
        result = app.handle_get_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.BAD_REQUEST

    def test_returns_403_when_accessing_another_user(self):
        event = _make_event("GET", user_id_path="other-user", auth_user_id="u-1")
        result = app.handle_get_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.FORBIDDEN

    def test_calls_service_when_authorized(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.get_user.return_value = _ok_response()
            event = _make_event("GET", user_id_path="u-1", auth_user_id="u-1")
            app.handle_get_user(event, "u-1", "req")
        mock_svc.get_user.assert_called_once_with("u-1", "req")


# ── handle_post_user ───────────────────────────────────────────────────────

class TestHandlePostUser:
    def test_returns_400_when_user_id_missing_from_body(self):
        event = _make_event("POST", body={})
        result = app.handle_post_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "USER_ID_REQUIRED"

    def test_returns_403_when_user_id_differs_from_auth(self):
        event = _make_event("POST", body={"userId": "other-user"})
        result = app.handle_post_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.FORBIDDEN

    def test_returns_400_on_invalid_json_body(self):
        event = _make_event("POST")
        event["body"] = "{bad json"
        result = app.handle_post_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.BAD_REQUEST

    def test_calls_service_when_authorized(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.create_user.return_value = {
                "statusCode": 201,
                "headers": {},
                "body": json.dumps({"user": {"userId": "u-1"}}),
            }
            event = _make_event("POST", body={"userId": "u-1"})
            app.handle_post_user(event, "u-1", "req")
        mock_svc.create_user.assert_called_once()


# ── handle_patch_user ──────────────────────────────────────────────────────

class TestHandlePatchUser:
    def test_returns_400_when_user_id_missing_from_path(self):
        event = _make_event("PATCH", body={"email": "e@e.com"})
        event["pathParameters"] = {}
        result = app.handle_patch_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.BAD_REQUEST

    def test_returns_403_for_different_user(self):
        event = _make_event("PATCH", user_id_path="other", auth_user_id="u-1", body={"email": "e@e.com"})
        result = app.handle_patch_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.FORBIDDEN

    def test_calls_service_on_authorized_update(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.update_user.return_value = _ok_response()
            event = _make_event("PATCH", user_id_path="u-1", auth_user_id="u-1", body={"email": "new@e.com"})
            app.handle_patch_user(event, "u-1", "req")
        mock_svc.update_user.assert_called_once_with("u-1", {"email": "new@e.com"}, "req")


# ── handle_delete_user ─────────────────────────────────────────────────────

class TestHandleDeleteUser:
    def test_returns_403_for_different_user(self):
        event = _make_event("DELETE", user_id_path="other", auth_user_id="u-1")
        result = app.handle_delete_user(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.FORBIDDEN

    def test_calls_service_on_authorized_delete(self):
        with patch.object(app, "user_service") as mock_svc:
            mock_svc.delete_user.return_value = {
                "statusCode": 204, "headers": {}, "body": json.dumps(None)
            }
            event = _make_event("DELETE", user_id_path="u-1", auth_user_id="u-1")
            app.handle_delete_user(event, "u-1", "req")
        mock_svc.delete_user.assert_called_once_with("u-1", "req")
