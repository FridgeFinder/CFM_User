"""
Unit tests for functions/user_devices/user_device_repository.py
Covers: UserDeviceRepository CRUD/query behavior.
"""
from unittest.mock import MagicMock

from user_device_models import UserDeviceRecord
from user_device_repository import UserDeviceRepository


TABLE = "test-user-devices-table"


def _make_repo():
    mock_client = MagicMock()
    return mock_client, UserDeviceRepository(mock_client, TABLE)


def _device(user_id: str = "u-1", installation_id: str = "device-1") -> UserDeviceRecord:
    return UserDeviceRecord(
        userId=user_id,
        installationId=installation_id,
        token="tok-1",
        platform="ios",
    )


class TestUpsertDevice:
    def test_calls_put_item(self):
        mock_client, repo = _make_repo()

        repo.upsert_device(_device())

        mock_client.put_item.assert_called_once()
        kwargs = mock_client.put_item.call_args.kwargs
        assert kwargs["TableName"] == TABLE


class TestGetDevice:
    def test_returns_device_when_found(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {
            "Item": {
                "userId": {"S": "u-1"},
                "installationId": {"S": "device-1"},
                "token": {"S": "tok-1"},
                "platform": {"S": "ios"},
                "notificationsEnabled": {"BOOL": True},
                "createdAt": {"S": "2024-01-01T00:00:00.000Z"},
                "lastSeenAt": {"S": "2024-01-01T00:00:00.000Z"},
            }
        }

        device = repo.get_device("u-1", "device-1")

        assert device is not None
        assert device.userId == "u-1"
        assert device.installationId == "device-1"

    def test_returns_none_when_missing(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {}

        assert repo.get_device("u-1", "device-1") is None


class TestListDevicesForUser:
    def test_returns_device_list(self):
        mock_client, repo = _make_repo()
        mock_client.query.return_value = {
            "Items": [
                {
                    "userId": {"S": "u-1"},
                    "installationId": {"S": "device-1"},
                    "token": {"S": "tok-1"},
                    "platform": {"S": "ios"},
                    "notificationsEnabled": {"BOOL": True},
                    "createdAt": {"S": "2024-01-01T00:00:00.000Z"},
                    "lastSeenAt": {"S": "2024-01-01T00:00:00.000Z"},
                }
            ]
        }

        devices = repo.list_devices_for_user("u-1")

        assert len(devices) == 1
        assert devices[0].installationId == "device-1"
        kwargs = mock_client.query.call_args.kwargs
        assert kwargs["TableName"] == TABLE
        assert kwargs["KeyConditionExpression"] == "userId = :user_id"


class TestDeleteDevice:
    def test_calls_delete_item(self):
        mock_client, repo = _make_repo()

        repo.delete_device("u-1", "device-1")

        mock_client.delete_item.assert_called_once()
        kwargs = mock_client.delete_item.call_args.kwargs
        assert kwargs["TableName"] == TABLE


class TestFindByToken:
    def test_queries_token_index(self):
        mock_client, repo = _make_repo()
        mock_client.query.return_value = {"Items": []}

        repo.find_by_token("tok-1")

        kwargs = mock_client.query.call_args.kwargs
        assert kwargs["IndexName"] == "token-index"
        assert kwargs["KeyConditionExpression"] == "token = :token"
