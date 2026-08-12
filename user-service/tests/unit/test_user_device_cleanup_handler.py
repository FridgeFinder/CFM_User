"""Unit tests for user_device_cleanup_handler.py."""
from unittest.mock import MagicMock, patch

import user_device_cleanup_handler as app


def _make_context(request_id: str = "req-test"):
    ctx = MagicMock()
    ctx.aws_request_id = request_id
    return ctx


class TestUserDeviceCleanupHandler:
    def test_ignores_event_without_user_id(self):
        result = app.lambda_handler({"detail": {}}, _make_context())

        assert result["status"] == "ignored"
        assert result["reason"] == "missing_user_id"

    def test_deletes_user_devices_for_user_id(self):
        event = {"detail": {"userId": "u-1"}}

        query_response = {
            "Items": [
                {"userId": {"S": "u-1"}, "installationId": {"S": "d-1"}},
                {"userId": {"S": "u-1"}, "installationId": {"S": "d-2"}},
            ]
        }

        with patch.object(app, "dynamodb") as mock_dynamodb:
            mock_dynamodb.query.return_value = query_response
            mock_dynamodb.batch_write_item.return_value = {"UnprocessedItems": {}}

            result = app.lambda_handler(event, _make_context())

        assert result["status"] == "deleted"
        assert result["userId"] == "u-1"
        assert result["deletedCount"] == 2
        mock_dynamodb.query.assert_called_once()
        mock_dynamodb.batch_write_item.assert_called_once()

    def test_handles_pagination(self):
        event = {"detail": {"userId": "u-1"}}

        first_page = {
            "Items": [{"userId": {"S": "u-1"}, "installationId": {"S": "d-1"}}],
            "LastEvaluatedKey": {"userId": {"S": "u-1"}, "installationId": {"S": "d-1"}},
        }
        second_page = {
            "Items": [{"userId": {"S": "u-1"}, "installationId": {"S": "d-2"}}],
        }

        with patch.object(app, "dynamodb") as mock_dynamodb:
            mock_dynamodb.query.side_effect = [first_page, second_page]
            mock_dynamodb.batch_write_item.return_value = {"UnprocessedItems": {}}

            result = app.lambda_handler(event, _make_context())

        assert result["status"] == "deleted"
        assert result["deletedCount"] == 2
        assert mock_dynamodb.query.call_count == 2
