"""
Unit tests for functions/user_service/service.py
Covers: UserService – create_user, get_user, update_user, delete_user.
UserRepository is fully mocked.
"""
import json
import pytest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

# conftest.py adds functions/user_service to sys.path
from service import UserService
from repository import UserRepository
from models import User
from http_utils import HttpStatus


def _make_service():
    mock_repo = MagicMock(spec=UserRepository)
    svc = UserService(mock_repo)
    return mock_repo, svc


def _sample_user(user_id: str = "u-1") -> User:
    return User(userId=user_id, username="testuser", email="test@test.com")


# ── create_user ────────────────────────────────────────────────────────────

class TestCreateUser:
    def test_returns_201_on_success(self):
        mock_repo, svc = _make_service()
        result = svc.create_user({"userId": "new-user"})

        assert result["statusCode"] == HttpStatus.CREATED
        body = json.loads(result["body"])
        assert "user" in body
        assert body["user"]["userId"] == "new-user"
        mock_repo.create_user.assert_called_once()

    def test_returns_400_on_validation_error(self):
        _, svc = _make_service()
        # Invalid email should cause a validation error
        result = svc.create_user({"userId": "u1", "email": "not-an-email"})

        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_returns_409_when_user_already_exists(self):
        mock_repo, svc = _make_service()
        mock_repo.create_user.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": ""}},
            "PutItem",
        )
        result = svc.create_user({"userId": "dup-user"})

        assert result["statusCode"] == HttpStatus.CONFLICT
        body = json.loads(result["body"])
        assert body["error"]["code"] == "ITEM_ALREADY_EXISTS"

    def test_propagates_unexpected_client_error(self):
        mock_repo, svc = _make_service()
        mock_repo.create_user.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "boom"}},
            "PutItem",
        )
        with pytest.raises(ClientError):
            svc.create_user({"userId": "u1"})

    def test_default_user_type_is_neighbor(self):
        _, svc = _make_service()
        result = svc.create_user({"userId": "u1"})
        body = json.loads(result["body"])
        assert body["user"]["userType"] == "Neighbor"


# ── get_user ───────────────────────────────────────────────────────────────

class TestGetUser:
    def test_returns_200_with_user_data(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = _sample_user("u-1")

        result = svc.get_user("u-1")

        assert result["statusCode"] == HttpStatus.OK
        body = json.loads(result["body"])
        assert body["user"]["userId"] == "u-1"

    def test_returns_404_when_not_found(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = None

        result = svc.get_user("ghost")

        assert result["statusCode"] == HttpStatus.NOT_FOUND
        body = json.loads(result["body"])
        assert body["error"]["code"] == "ITEM_NOT_FOUND"

    def test_includes_request_id_header(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = _sample_user()

        result = svc.get_user("u-1", request_id="req-abc")

        assert result["headers"]["X-Request-Id"] == "req-abc"


# ── update_user ────────────────────────────────────────────────────────────

class TestUpdateUser:
    def test_returns_200_on_successful_update(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = _sample_user("u-1")

        result = svc.update_user("u-1", {"email": "new@example.com"})

        assert result["statusCode"] == HttpStatus.OK
        body = json.loads(result["body"])
        assert body["user"]["email"] == "new@example.com"
        mock_repo.update_user.assert_called_once()

    def test_returns_400_on_empty_body(self):
        _, svc = _make_service()

        result = svc.update_user("u-1", {})

        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "EMPTY_REQUEST_BODY"

    def test_returns_404_when_user_not_found(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = None

        result = svc.update_user("fake-user", {"email": "e@e.com"})

        assert result["statusCode"] == HttpStatus.NOT_FOUND
        body = json.loads(result["body"])
        assert body["error"]["code"] == "ITEM_NOT_FOUND"

    def test_returns_400_on_validation_error(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = _sample_user("u-1")

        result = svc.update_user("u-1", {"email": "bad-email"})

        assert result["statusCode"] == HttpStatus.BAD_REQUEST
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_does_not_call_repo_update_on_validation_error(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = _sample_user("u-1")

        svc.update_user("u-1", {"email": "bad-email"})

        mock_repo.update_user.assert_not_called()

    def test_passes_previous_last_updated_to_repo(self):
        mock_repo, svc = _make_service()
        user = _sample_user("u-1")
        original_last_updated = user.lastUpdated
        mock_repo.get_user_by_id.return_value = user

        svc.update_user("u-1", {"email": "new@example.com"})

        # update_user is called as update_user(user_dict, previous_last_updated)
        assert mock_repo.update_user.call_args.args[1] == original_last_updated

    def test_returns_409_on_write_conflict(self):
        mock_repo, svc = _make_service()
        mock_repo.get_user_by_id.return_value = _sample_user("u-1")
        mock_repo.update_user.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": ""}},
            "PutItem",
        )

        result = svc.update_user("u-1", {"email": "new@example.com"})

        assert result["statusCode"] == HttpStatus.CONFLICT
        body = json.loads(result["body"])
        assert body["error"]["code"] == "WRITE_CONFLICT"


# ── delete_user ────────────────────────────────────────────────────────────

class TestDeleteUser:
    def test_returns_204_on_success(self):
        mock_repo, svc = _make_service()
        mock_repo.user_exists.return_value = True

        result = svc.delete_user("u-1")

        assert result["statusCode"] == HttpStatus.NO_CONTENT
        mock_repo.delete_user.assert_called_once_with("u-1")

    def test_returns_404_when_user_not_found(self):
        mock_repo, svc = _make_service()
        mock_repo.user_exists.return_value = False

        result = svc.delete_user("ghost")

        assert result["statusCode"] == HttpStatus.NOT_FOUND
        body = json.loads(result["body"])
        assert body["error"]["code"] == "ITEM_NOT_FOUND"

    def test_does_not_call_repo_delete_when_not_found(self):
        mock_repo, svc = _make_service()
        mock_repo.user_exists.return_value = False

        svc.delete_user("ghost")

        mock_repo.delete_user.assert_not_called()
