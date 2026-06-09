"""
Unit tests for functions/user_service/repository.py
Covers: UserRepository – get_user_by_id, create_user, update_user,
    delete_user, user_exists, is_username_available.
All DynamoDB calls are mocked.
"""
import pytest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

# conftest.py adds functions/user_service to sys.path
from repository import UserRepository
from models import User


TABLE = "test-users-table"


def _make_repo():
    mock_client = MagicMock()
    return mock_client, UserRepository(mock_client, TABLE)


def _dynamo_user_item(user_id: str = "u-1") -> dict:
    """Minimal DynamoDB AttributeValue item for a User."""
    return {
        "userId": {"S": user_id},
        "userType": {"S": "Neighbor"},
        "points": {"N": "0"},
        "settings": {
            "M": {
                "pushNotificationEnabled": {"BOOL": False},
                "emailNotificationEnabled": {"BOOL": True},
                "geofenceEnabled": {"BOOL": False},
            }
        },
        "createdAt": {"S": "2024-01-01T00:00:00.000Z"},
        "lastUpdated": {"S": "2024-01-01T00:00:00.000Z"},
        "lastLoginAt": {"S": "2024-01-01T00:00:00.000Z"},
    }


# ── get_user_by_id ─────────────────────────────────────────────────────────

class TestGetUserById:
    def test_returns_user_when_found(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {"Item": _dynamo_user_item("u-1")}

        user = repo.get_user_by_id("u-1")

        assert isinstance(user, User)
        assert user.userId == "u-1"
        mock_client.get_item.assert_called_once()
        call_kwargs = mock_client.get_item.call_args.kwargs
        assert call_kwargs["TableName"] == TABLE

    def test_returns_none_when_not_found(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {}

        user = repo.get_user_by_id("missing-user")

        assert user is None

    def test_propagates_client_error(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": ""}},
            "GetItem",
        )
        with pytest.raises(ClientError):
            repo.get_user_by_id("u-1")


# ── create_user ────────────────────────────────────────────────────────────

class TestCreateUser:
    def test_calls_put_item_with_condition(self):
        mock_client, repo = _make_repo()
        user_data = {"userId": "new-user", "userType": "Neighbor"}

        repo.create_user(user_data)

        mock_client.put_item.assert_called_once()
        kwargs = mock_client.put_item.call_args.kwargs
        assert kwargs["TableName"] == TABLE
        assert kwargs["ConditionExpression"] == "attribute_not_exists(userId)"

    def test_raises_on_conditional_check_failed(self):
        mock_client, repo = _make_repo()
        mock_client.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": ""}},
            "PutItem",
        )
        with pytest.raises(ClientError) as exc_info:
            repo.create_user({"userId": "dup"})
        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


# ── update_user ────────────────────────────────────────────────────────────

class TestUpdateUser:
    def test_calls_put_item_with_optimistic_lock_condition(self):
        mock_client, repo = _make_repo()
        user_data = {"userId": "u-1", "userType": "Volunteer", "lastUpdated": "2024-01-02T00:00:00.000Z"}
        prev_ts = "2024-01-01T00:00:00.000Z"

        repo.update_user(user_data, previous_last_updated=prev_ts)

        mock_client.put_item.assert_called_once()
        kwargs = mock_client.put_item.call_args.kwargs
        assert kwargs["TableName"] == TABLE
        assert kwargs["ConditionExpression"] == "lastUpdated = :prev_last_updated"
        assert ":prev_last_updated" in kwargs["ExpressionAttributeValues"]

    def test_raises_on_concurrent_modification(self):
        mock_client, repo = _make_repo()
        mock_client.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": ""}},
            "PutItem",
        )
        with pytest.raises(ClientError) as exc_info:
            repo.update_user({"userId": "u-1"}, previous_last_updated="2024-01-01T00:00:00.000Z")
        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


# ── delete_user ────────────────────────────────────────────────────────────

class TestDeleteUser:
    def test_calls_delete_item(self):
        mock_client, repo = _make_repo()

        repo.delete_user("u-1")

        mock_client.delete_item.assert_called_once()
        kwargs = mock_client.delete_item.call_args.kwargs
        assert kwargs["TableName"] == TABLE

    def test_delete_item_key_contains_user_id(self):
        mock_client, repo = _make_repo()

        repo.delete_user("u-to-delete")

        kwargs = mock_client.delete_item.call_args.kwargs
        # Key must contain the userId in serialized DynamoDB format
        assert "userId" in kwargs["Key"]
        # TypeSerializer serializes a string as {"S": value}
        assert kwargs["Key"]["userId"] == {"S": "u-to-delete"}


# ── user_exists ────────────────────────────────────────────────────────────

class TestUserExists:
    def test_returns_true_when_user_found(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {"Item": {"userId": {"S": "u-1"}}}
        assert repo.user_exists("u-1") is True

    def test_returns_false_when_user_not_found(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {}
        assert repo.user_exists("ghost") is False

    def test_uses_projection_expression_to_limit_response(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {"Item": {"userId": {"S": "u-1"}}}

        repo.user_exists("u-1")

        kwargs = mock_client.get_item.call_args.kwargs
        assert kwargs.get("ProjectionExpression") == "userId"

    def test_calls_get_item_once_not_full_user_fetch(self):
        mock_client, repo = _make_repo()
        mock_client.get_item.return_value = {}

        repo.user_exists("u-1")

        mock_client.get_item.assert_called_once()


# ── is_username_available ─────────────────────────────────────────────────

class TestIsUsernameAvailable:
    def test_returns_true_when_count_is_zero(self):
        mock_client, repo = _make_repo()
        mock_client.query.return_value = {"Count": 0}

        assert repo.is_username_available("new_name") is True

    def test_returns_false_when_count_is_non_zero(self):
        mock_client, repo = _make_repo()
        mock_client.query.return_value = {"Count": 1}

        assert repo.is_username_available("taken_name") is False

    def test_queries_username_index_with_expected_expression(self):
        mock_client, repo = _make_repo()
        mock_client.query.return_value = {"Count": 0}

        repo.is_username_available("my_name")

        kwargs = mock_client.query.call_args.kwargs
        assert kwargs["TableName"] == TABLE
        assert kwargs["IndexName"] == "username-index"
        assert kwargs["KeyConditionExpression"] == "username = :username"
        assert kwargs["ExpressionAttributeValues"] == {":username": {"S": "my_name"}}
        assert kwargs["Limit"] == 1
        assert kwargs["Select"] == "COUNT"
