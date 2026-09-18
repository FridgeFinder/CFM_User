"""
Unit tests for functions/username_check/app.py
Covers: is_username_available, lambda_handler.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from http_utils import HttpStatus
import username_check_handler as username_check_app

# ── is_username_available ──────────────────────────────────────────────────

class TestIsUsernameAvailable:
    def test_returns_true_when_count_is_zero(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 0}
            result = username_check_app.is_username_available("free_name")

        assert result is True

    def test_returns_false_when_count_is_nonzero(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 1}
            result = username_check_app.is_username_available("taken_name")

        assert result is False

    def test_raises_when_count_key_missing(self):#should never happen since DynamoDB always returns Count
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {}
            with pytest.raises(KeyError):
                username_check_app.is_username_available("name")

    def test_queries_correct_index(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 0}
            username_check_app.is_username_available("myuser")

        kwargs = mock_ddb.query.call_args.kwargs
        assert kwargs["IndexName"] == "username-index"

    def test_passes_username_as_expression_value(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 0}
            username_check_app.is_username_available("avacado-toast")

        kwargs = mock_ddb.query.call_args.kwargs
        assert kwargs["ExpressionAttributeValues"][":username"] == {"S": "avacado-toast"}

    def test_propagates_dynamodb_exception(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.side_effect = RuntimeError("DynamoDB error")
            with pytest.raises(RuntimeError):
                username_check_app.is_username_available("name")


# ── lambda_handler ─────────────────────────────────────────────────────────

def _make_event(username: str = None) -> dict:
    params = {"username": username} if username else {}
    return {"pathParameters": params}


def _make_context(request_id: str = "req-check") -> MagicMock:
    ctx = MagicMock()
    ctx.aws_request_id = request_id
    return ctx


class TestUsernameCheckLambdaHandler:
    def test_returns_400_when_username_missing(self):
        result = username_check_app.lambda_handler(
            {"pathParameters": {}}, _make_context()
        )
        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_returns_400_when_username_too_short(self):
        result = username_check_app.lambda_handler(
            _make_event("ab"), _make_context()
        )
        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_returns_400_when_username_has_invalid_chars(self):
        result = username_check_app.lambda_handler(
            _make_event("bad name!"), _make_context()
        )
        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_returns_200_with_available_true(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 0}
            result = username_check_app.lambda_handler(
                _make_event("free_name"), _make_context()
            )

        assert result["statusCode"] == HttpStatus.OK
        body = json.loads(result["body"])
        assert body["available"] is True

    def test_returns_200_with_available_false(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 1}
            result = username_check_app.lambda_handler(
                _make_event("taken_name"), _make_context()
            )

        assert result["statusCode"] == HttpStatus.OK
        body = json.loads(result["body"])
        assert body["available"] is False

    def test_returns_500_on_dynamodb_exception(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.side_effect = RuntimeError("DB exploded")
            result = username_check_app.lambda_handler(
                _make_event("name"), _make_context()
            )

        assert result["statusCode"] == HttpStatus.INTERNAL_SERVER_ERROR
        body = json.loads(result["body"])
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"

    def test_uses_context_request_id(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 0}
            result = username_check_app.lambda_handler(
                _make_event("name"), _make_context("req-id-42")
            )

        assert result["headers"]["X-Request-Id"] == "req-id-42"

    def test_response_body_contains_available_key(self):
        with patch.object(username_check_app, "dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Count": 0}
            result = username_check_app.lambda_handler(
                _make_event("myuser"), _make_context()
            )

        body = json.loads(result["body"])
        assert "available" in body
