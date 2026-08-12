"""
Unit tests for functions/user_service/utils.py
Covers: get_authenticated_user_id.
"""
# conftest.py already set up sys.path
from utils import get_authenticated_user_id


class TestGetAuthenticatedUserId:
    def _make_event(self, sub=None):
        event = {"requestContext": {"authorizer": {"jwt": {"claims": {}}}}}
        if sub is not None:
            event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"] = sub
        return event

    def test_returns_sub_from_jwt_claims(self):
        event = self._make_event(sub="firebase-uid-abc")
        assert get_authenticated_user_id(event) == "firebase-uid-abc"

    def test_returns_none_when_no_sub(self):
        event = self._make_event()
        assert get_authenticated_user_id(event) is None

    def test_returns_none_when_no_jwt(self):
        event = {"requestContext": {"authorizer": {}}}
        assert get_authenticated_user_id(event) is None

    def test_returns_none_when_no_authorizer(self):
        event = {"requestContext": {}}
        assert get_authenticated_user_id(event) is None

    def test_returns_none_when_no_request_context(self):
        assert get_authenticated_user_id({}) is None
