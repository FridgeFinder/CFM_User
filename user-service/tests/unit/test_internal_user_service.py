"""
Unit tests for functions/internal_user_service/app.py
Covers: _dynamodb_to_dict, get_user_details, lambda_handler.
"""
import json
from unittest.mock import MagicMock, patch
from http_utils import HttpStatus
import internal_user_service_handler as internal_app

# ── _dynamodb_to_dict ──────────────────────────────────────────────────────

class TestDynamodbToDict:
    def test_string_type(self):
        result = internal_app._dynamodb_to_dict({"email": {"S": "a@b.com"}})
        assert result == {"email": "a@b.com"}

    def test_number_type(self):
        result = internal_app._dynamodb_to_dict({"count": {"N": "42"}})
        assert result == {"count": 42}

    def test_bool_type(self):
        result = internal_app._dynamodb_to_dict({"active": {"BOOL": True}})
        assert result == {"active": True}

    def test_null_type(self):
        result = internal_app._dynamodb_to_dict({"field": {"NULL": True}})
        assert result == {"field": None}

    def test_nested_map_type(self):
        item = {
            "settings": {
                "M": {
                    "pushNotificationEnabled": {"BOOL": False},
                    "geofenceEnabled": {"BOOL": True},
                }
            }
        }
        result = internal_app._dynamodb_to_dict(item)
        assert result["settings"]["pushNotificationEnabled"] is False
        assert result["settings"]["geofenceEnabled"] is True

    def test_list_type_with_strings(self):
        item = {"tags": {"L": [{"S": "a"}, {"S": "b"}]}}
        result = internal_app._dynamodb_to_dict(item)
        assert result["tags"] == ["a", "b"]

    def test_multiple_fields(self):
        item = {
            "email": {"S": "x@y.com"},
            "fcmToken": {"S": "tok123"},
        }
        result = internal_app._dynamodb_to_dict(item)
        assert result["email"] == "x@y.com"
        assert result["fcmToken"] == "tok123"


# ── get_user_details ───────────────────────────────────────────────────────

class TestGetUserDetails:
    def _mock_logger(self):
        import logging
        return MagicMock(spec=logging.LoggerAdapter)

    def test_returns_projected_dict_when_found(self):
        item = {
            "email": {"S": "u@example.com"},
            "fcmToken": {"S": "tok"},
            "settings": {"M": {"pushNotificationEnabled": {"BOOL": True}}},
        }
        with patch.object(internal_app, "dynamodb") as mock_ddb:
            mock_ddb.get_item.return_value = {"Item": item}
            result = internal_app.get_user_details("u-1", self._mock_logger())

        assert result["email"] == "u@example.com"
        assert result["fcmToken"] == "tok"

    def test_returns_none_when_not_found(self):
        with patch.object(internal_app, "dynamodb") as mock_ddb:
            mock_ddb.get_item.return_value = {}
            result = internal_app.get_user_details("user-not-exist", self._mock_logger())

        assert result is None

    def test_uses_projection_expression(self):
        with patch.object(internal_app, "dynamodb") as mock_ddb:
            mock_ddb.get_item.return_value = {}
            internal_app.get_user_details("u-1", self._mock_logger())

        kwargs = mock_ddb.get_item.call_args.kwargs
        assert "ProjectionExpression" in kwargs
        assert "email" in kwargs["ProjectionExpression"]
        assert "fcmToken" in kwargs["ProjectionExpression"]
        assert "settings" in kwargs["ProjectionExpression"]


# ── lambda_handler ─────────────────────────────────────────────────────────

def _make_event(method="GET", user_id="u-1"):
    return {
        "requestContext": {"http": {"method": method}},
        "pathParameters": {"userId": user_id} if user_id else None,
    }


def _make_context(request_id="req-internal"):
    ctx = MagicMock()
    ctx.aws_request_id = request_id
    return ctx


class TestInternalLambdaHandler:
    def _found_item(self):
        return {
            "email": {"S": "u@example.com"},
            "settings": {"M": {}},
        }

    def test_returns_200_when_user_found(self):
        with patch.object(internal_app, "dynamodb") as mock_ddb:
            mock_ddb.get_item.return_value = {"Item": self._found_item()}
            result = internal_app.lambda_handler(_make_event("GET", "u-1"), _make_context())

        assert result["statusCode"] == HttpStatus.OK
        body = json.loads(result["body"])
        assert "user" in body

    def test_returns_404_when_user_not_found(self):
        with patch.object(internal_app, "dynamodb") as mock_ddb:
            mock_ddb.get_item.return_value = {}
            result = internal_app.lambda_handler(_make_event("GET", "u-1"), _make_context())

        assert result["statusCode"] == HttpStatus.NOT_FOUND
        body = json.loads(result["body"])
        assert body["error"]["code"] == "ITEM_NOT_FOUND"

    def test_returns_405_for_non_get_method(self):
        result = internal_app.lambda_handler(_make_event("POST", "u-1"), _make_context())
        assert result["statusCode"] == HttpStatus.METHOD_NOT_ALLOWED

    def test_returns_400_when_user_id_missing(self):
        event = {"requestContext": {"http": {"method": "GET"}}, "pathParameters": {}}
        result = internal_app.lambda_handler(event, _make_context())
        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "USER_ID_REQUIRED"

    def test_returns_400_when_path_parameters_is_none(self):
        event = {"requestContext": {"http": {"method": "GET"}}, "pathParameters": None}
        result = internal_app.lambda_handler(event, _make_context())
        assert result["statusCode"] == HttpStatus.BAD_REQUEST

    def test_returns_500_on_dynamodb_exception(self):
        with patch.object(internal_app, "dynamodb") as mock_ddb:
            mock_ddb.get_item.side_effect = RuntimeError("DB down")
            result = internal_app.lambda_handler(_make_event("GET", "u-1"), _make_context())

        assert result["statusCode"] == HttpStatus.INTERNAL_SERVER_ERROR

    def test_uses_context_request_id(self):
        with patch.object(internal_app, "dynamodb") as mock_ddb:
            mock_ddb.get_item.return_value = {"Item": self._found_item()}
            result = internal_app.lambda_handler(_make_event(), _make_context("req-xyz"))

        assert result["headers"]["X-Request-Id"] == "req-xyz"
