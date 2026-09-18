"""
Unit tests for functions/user_devices/user_device_service.py
Covers: UserDeviceService register and unregister behavior.
"""
import json
from unittest.mock import MagicMock

from http_utils import HttpStatus
from user_device_service import UserDeviceService
from user_device_repository import UserDeviceRepository
from user_device_models import UserDeviceRecord


def _make_service():
    mock_repo = MagicMock(spec=UserDeviceRepository)
    return mock_repo, UserDeviceService(mock_repo)


class TestRegisterDevice:
    def test_returns_204_on_success(self):
        mock_repo, svc = _make_service()

        result = svc.register_device("u-1", "device-1", "tok-1", "ios")

        assert result["statusCode"] == HttpStatus.NO_CONTENT
        mock_repo.upsert_device.assert_called_once()

    def test_returns_400_for_invalid_platform(self):
        mock_repo, svc = _make_service()

        result = svc.register_device("u-1", "device-1", "tok-1", "nintendo")

        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"
        mock_repo.upsert_device.assert_not_called()


class TestUnregisterDevice:
    def test_returns_204_and_deletes_device(self):
        mock_repo, svc = _make_service()

        result = svc.unregister_device("u-1", "device-1")

        assert result["statusCode"] == HttpStatus.NO_CONTENT
        mock_repo.delete_device.assert_called_once_with("u-1", "device-1")


class TestGetDevice:
    def test_returns_200_when_device_exists(self):
        mock_repo, svc = _make_service()
        mock_repo.get_device.return_value = UserDeviceRecord(userId="u-1", installationId="device-1", token="tok-1", platform="ios")

        result = svc.get_device("u-1", "device-1")

        assert result["statusCode"] == HttpStatus.OK
        mock_repo.get_device.assert_called_once_with("u-1", "device-1")

    def test_returns_404_when_device_missing(self):
        mock_repo, svc = _make_service()
        mock_repo.get_device.return_value = None

        result = svc.get_device("u-1", "device-1")

        assert result["statusCode"] == HttpStatus.NOT_FOUND
        mock_repo.get_device.assert_called_once_with("u-1", "device-1")


class TestUpdateDevice:
    def test_returns_200_and_updates_allowed_fields(self):
        mock_repo, svc = _make_service()
        existing = UserDeviceRecord(userId="u-1", installationId="device-1", token="tok-1", platform="ios")
        mock_repo.get_device.return_value = existing

        result = svc.update_device("u-1", "device-1", {"notificationsEnabled": False})

        assert result["statusCode"] == HttpStatus.OK
        mock_repo.upsert_device.assert_called_once()

    def test_returns_400_for_empty_updates(self):
        mock_repo, svc = _make_service()

        result = svc.update_device("u-1", "device-1", {})

        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        mock_repo.get_device.assert_not_called()
        mock_repo.upsert_device.assert_not_called()

    def test_returns_400_for_unsupported_field(self):
        mock_repo, svc = _make_service()

        result = svc.update_device("u-1", "device-1", {"token": "new-token"})

        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        mock_repo.get_device.assert_not_called()
        mock_repo.upsert_device.assert_not_called()

    def test_returns_404_when_device_missing(self):
        mock_repo, svc = _make_service()
        mock_repo.get_device.return_value = None

        result = svc.update_device("u-1", "device-1", {"notificationsEnabled": False})

        assert result["statusCode"] == HttpStatus.NOT_FOUND
        mock_repo.get_device.assert_called_once_with("u-1", "device-1")
        mock_repo.upsert_device.assert_not_called()
