"""
Unit tests for functions/user_devices/user_device_service_handler.py
Covers: route handling, auth checks, and request validation for user-device APIs.
"""
import json
from unittest.mock import MagicMock, patch

from http_utils import HttpStatus
import user_device_service_handler as app


def _make_context(request_id: str = "req-test"):
    ctx = MagicMock()
    ctx.aws_request_id = request_id
    return ctx


def _make_event(
    method: str = "POST",
    path: str = "/v1/users/u-1/user-devices/device-1",
    user_id_path: str = "u-1",
    installation_id_path: str = "device-1",
    auth_user_id: str = "u-1",
    body: dict = None,
) -> dict:
    event = {
        "requestContext": {
            "http": {"method": method},
            "authorizer": {"jwt": {"claims": {"sub": auth_user_id}}},
        },
        "rawPath": path,
        "pathParameters": {"userId": user_id_path, "installationId": installation_id_path},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


class TestPathHelpers:
    def test_get_user_id_from_path(self):
        user_id, error = app.get_user_id_from_path({"pathParameters": {"userId": "u-1"}})
        assert user_id == "u-1"
        assert error is None

    def test_get_installation_id_from_path(self):
        installation_id, error = app.get_installation_id_from_path({"pathParameters": {"installationId": "d-1"}})
        assert installation_id == "d-1"
        assert error is None


class TestLambdaRouting:
    def test_get_routes_to_fetch(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.get_device.return_value = {
                "statusCode": 200,
                "headers": {},
                "body": json.dumps({"device": {"userId": "u-1", "installationId": "device-1", "token": "tok"}}),
            }
            result = app.lambda_handler(_make_event("GET"), _make_context())
        mock_svc.get_device.assert_called_once()
        assert result["statusCode"] == 200

    def test_post_routes_to_register(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.register_device.return_value = {
                "statusCode": 204,
                "headers": {},
                "body": json.dumps(None),
            }
            result = app.lambda_handler(_make_event("POST", body={"token": "tok"}), _make_context())
        mock_svc.register_device.assert_called_once()
        assert result["statusCode"] == 204

    def test_delete_routes_to_unregister(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.unregister_device.return_value = {
                "statusCode": 204,
                "headers": {},
                "body": json.dumps(None),
            }
            result = app.lambda_handler(_make_event("DELETE"), _make_context())
        mock_svc.unregister_device.assert_called_once()
        assert result["statusCode"] == 204

    def test_patch_routes_to_update(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.update_device.return_value = {
                "statusCode": 200,
                "headers": {},
                "body": json.dumps({"device": {"userId": "u-1", "installationId": "device-1", "token": "tok", "notificationsEnabled": False}}),
            }
            result = app.lambda_handler(_make_event("PATCH", body={"notificationsEnabled": False}), _make_context())
        mock_svc.update_device.assert_called_once()
        assert result["statusCode"] == 200


class TestHandlers:
    def test_get_calls_service(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.get_device.return_value = {
                "statusCode": 200,
                "headers": {},
                "body": json.dumps({"device": {"userId": "u-1", "installationId": "device-1", "token": "tok"}}),
            }
            event = _make_event(method="GET")
            app.handle_get_user_device(event, "u-1", "req")

        mock_svc.get_device.assert_called_once_with(
            user_id="u-1",
            installation_id="device-1",
            request_id="req",
        )

    def test_register_rejects_other_user(self):
        event = _make_event(auth_user_id="u-2", user_id_path="u-1", body={"token": "tok"})
        result = app.handle_post_user_device(event, "u-2", "req")
        assert result["statusCode"] == HttpStatus.FORBIDDEN

    def test_register_requires_token(self):
        event = _make_event(body={})
        result = app.handle_post_user_device(event, "u-1", "req")
        assert result["statusCode"] == HttpStatus.BAD_REQUEST

    def test_register_calls_service(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.register_device.return_value = {
                "statusCode": 204,
                "headers": {},
                "body": json.dumps(None),
            }
            event = _make_event(body={"token": "tok", "platform": "ios"})
            app.handle_post_user_device(event, "u-1", "req")

        mock_svc.register_device.assert_called_once_with(
            user_id="u-1",
            installation_id="device-1",
            token="tok",
            platform="ios",
            request_id="req",
        )

    def test_unregister_calls_service(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.unregister_device.return_value = {
                "statusCode": 204,
                "headers": {},
                "body": json.dumps(None),
            }
            event = _make_event(method="DELETE")
            app.handle_delete_user_device(event, "u-1", "req")

        mock_svc.unregister_device.assert_called_once_with(
            user_id="u-1",
            installation_id="device-1",
            request_id="req",
        )

    def test_patch_calls_service(self):
        with patch.object(app, "user_device_service") as mock_svc:
            mock_svc.update_device.return_value = {
                "statusCode": 200,
                "headers": {},
                "body": json.dumps({"device": {"userId": "u-1", "installationId": "device-1", "token": "tok", "notificationsEnabled": False}}),
            }
            event = _make_event(method="PATCH", body={"notificationsEnabled": False})
            app.handle_patch_user_device(event, "u-1", "req")

        mock_svc.update_device.assert_called_once_with(
            user_id="u-1",
            installation_id="device-1",
            updates={"notificationsEnabled": False},
            request_id="req",
        )

    def test_patch_rejects_other_user(self):
        event = _make_event(method="PATCH", auth_user_id="u-2", user_id_path="u-1", body={"notificationsEnabled": False})
        result = app.handle_patch_user_device(event, "u-2", "req")
        assert result["statusCode"] == HttpStatus.FORBIDDEN
