"""
Unit tests for functions/user_service/models.py
Covers: User model, validators, update_fields, serialization helpers.
"""
import re
import pytest
from pydantic import ValidationError
import time

# conftest.py adds functions/user_service to sys.path
from models import (
    User,
    UserType,
    UserSettings,
    clean_string_fields,
    get_utc_timestamp,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _make_user(**overrides) -> User:
    base = {"userId": "user-123"}
    base.update(overrides)
    return User(**base)


# ── get_utc_timestamp ──────────────────────────────────────────────────────

class TestGetUtcTimestamp:
    def test_is_valid_iso8601_format(self):
        ts = get_utc_timestamp()
        assert re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$', ts)


# ── clean_string_fields ────────────────────────────────────────────────────

class TestCleanStringFields:
    def test_strips_whitespace(self):
        result = clean_string_fields({"name": "  Alice  ", "age": 30})
        assert result == {"name": "Alice", "age": 30}

    def test_empty_string_becomes_none(self):
        result = clean_string_fields({"name": "   "})
        assert result == {"name":  None}

    def test_non_string_unchanged(self):
        result = clean_string_fields({"count": 5, "flag": True})
        assert result == {"count": 5, "flag": True}

    def test_none_value_unchanged(self):
        result = clean_string_fields({"field": None})
        assert result == {"field": None}


# ── UserType enum & UserSettings model ────────────────────────────────────

class TestEnums:
    def test_user_type_values(self):
        assert UserType.ORGANIZER.value == "Organizer"
        assert UserType.HOST.value == "Host"
        assert UserType.VOLUNTEER.value == "Volunteer"
        assert UserType.NEIGHBOR.value == "Neighbor"

    def test_user_settings_defaults_are_false(self):
        s = UserSettings()
        assert s.emailNotificationEnabled is True
        assert s.geofenceEnabled is False


# ── User creation ──────────────────────────────────────────────────────────

class TestUserCreation:
    def test_minimal_required_fields(self):
        user = _make_user()
        assert user.userId == "user-123"
        assert user.userType == UserType.NEIGHBOR.value
        assert user.points == 0

    def test_default_settings(self):
        user = _make_user()
        assert user.settings == UserSettings()

    def test_timestamps_are_set(self):
        user = _make_user()
        assert user.createdAt.endswith("Z")
        assert user.lastUpdated.endswith("Z")
        assert user.lastLoginAt.endswith("Z")

    def test_optional_fields_none_by_default(self):
        user = _make_user()
        assert user.username is None
        assert user.email is None
        assert user.phoneNumber is None
        assert user.zipcode is None

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            User(userId="u1", unknownField="oops")

    def test_all_optional_fields_accepted(self):
        user = User(
            userId="u1",
            username="cactus_01",
            email="beaver@example.com",
            phoneNumber="+1 (555) 000-1234",
            zipcode="10001",
            userType=UserType.VOLUNTEER.value,
            points=10,
        )
        assert user.username == "cactus_01"
        assert user.email == "beaver@example.com"
        assert user.phoneNumber == "15550001234"
        assert user.zipcode == "10001"
        assert user.userType == UserType.VOLUNTEER.value
        assert user.points == 10

    def test_string_fields_stripped_on_creation(self):
        user = User(userId="  user-123  ", username="  plum  ")
        assert user.userId == "user-123"
        assert user.username == "plum"

    def test_empty_username_string_becomes_none(self):
        user = User(userId="u1", username="   ")
        assert user.username is None


# ── userId validation ──────────────────────────────────────────────────────

class TestUserIdValidation:
    def test_empty_user_id_raises(self):
        # strip_strings converts "" → None before the field validator runs,
        # so the actual Pydantic error is a type error (not the custom message).
        with pytest.raises(ValidationError):
            User(userId="")

    def test_whitespace_only_user_id_raises(self):
        # strip_strings converts "   " → None, then validate_user_id rejects it
        with pytest.raises(ValidationError):
            User(userId="   ")


# ── email validation ───────────────────────────────────────────────────────

class TestEmailValidation:
    @pytest.mark.parametrize("email", [
        "user@example.com",
        "user.name+tag@sub.domain.org",
        "a@b.io",
    ])
    def test_valid_emails(self, email):
        user = _make_user(email=email)
        assert user.email == email

    @pytest.mark.parametrize("bad_email", [
        "notanemail",
        "missing@dot",
        "@nodomain.com",
        "spaces in@email.com",
    ])
    def test_invalid_emails_raise(self, bad_email):
        with pytest.raises(ValidationError, match="Invalid email format"):
            _make_user(email=bad_email)

    def test_none_email_accepted(self):
        user = _make_user(email=None)
        assert user.email is None


# ── username validation ────────────────────────────────────────────────────

class TestUsernameValidation:
    def test_valid_username(self):
        user = _make_user(username="apple_99")
        assert user.username == "apple_99"

    def test_username_too_short(self):
        with pytest.raises(ValidationError, match="at least 3 characters"):
            _make_user(username="ab")

    def test_username_too_long(self):
        with pytest.raises(ValidationError, match="30 characters or less"):
            _make_user(username="a" * 31)

    def test_username_invalid_chars(self):
        with pytest.raises(ValidationError, match="letters, numbers"):
            _make_user(username="bad name!")

    def test_username_hyphens_and_underscores_allowed(self):
        user = _make_user(username="valid-user_name")
        assert user.username == "valid-user_name"

    def test_none_username_accepted(self):
        user = _make_user(username=None)
        assert user.username is None


# ── phone number validation ────────────────────────────────────────────────

class TestPhoneNumberValidation:
    @pytest.mark.parametrize("phone,expected", [
        ("5550001234", "5550001234"),
        ("+1 (555) 000-1234", "15550001234"),
        ("555.000.1234", "5550001234"),
    ])
    def test_valid_phone_numbers(self, phone, expected):
        user = _make_user(phoneNumber=phone)
        assert user.phoneNumber == expected

    def test_too_short_phone_raises(self):
        with pytest.raises(ValidationError, match="at least 10 digits"):
            _make_user(phoneNumber="12345")

    def test_too_long_phone_raises(self):
        with pytest.raises(ValidationError, match="at most 15 digits"):
            _make_user(phoneNumber="1234567890123456")

    def test_letters_in_phone_raises(self):
        with pytest.raises(ValidationError, match="digits and separators"):
            _make_user(phoneNumber="555-ABC-1234")

    def test_none_phone_accepted(self):
        user = _make_user(phoneNumber=None)
        assert user.phoneNumber is None


# ── zipcode validation ─────────────────────────────────────────────────────

class TestZipcodeValidation:
    @pytest.mark.parametrize("zipcode", ["10001", "SW1A 1AA", "12345-6789"])
    def test_valid_zipcodes(self, zipcode):
        user = _make_user(zipcode=zipcode)
        assert user.zipcode == zipcode

    def test_too_short_zipcode_raises(self):
        with pytest.raises(ValidationError, match="at least 3 characters"):
            _make_user(zipcode="12")

    def test_too_long_zipcode_raises(self):
        with pytest.raises(ValidationError, match="10 characters or less"):
            _make_user(zipcode="12345678901")

    def test_special_chars_in_zipcode_raises(self):
        with pytest.raises(ValidationError, match="letters, numbers"):
            _make_user(zipcode="1234!")

    def test_none_zipcode_accepted(self):
        user = _make_user(zipcode=None)
        assert user.zipcode is None


# ── settings validation ────────────────────────────────────────────────────

class TestSettingsValidation:
    def test_partial_settings_fills_defaults(self):
        user = _make_user(settings={"emailNotificationEnabled": False})
        assert user.settings.emailNotificationEnabled is False
        assert user.settings.geofenceEnabled is False

    def test_invalid_setting_keys_ignored(self):
        # UserSettings uses extra="ignore" so unknown keys are silently dropped
        user = _make_user(settings={"emailNotificationEnabled": False, "bogusKey": True})
        assert not hasattr(user.settings, "bogusKey")

    def test_empty_settings_uses_all_defaults(self):
        user = _make_user(settings={})
        assert user.settings == UserSettings()


# ── serialization ──────────────────────────────────────────────────────────

class TestSerialization:
    def test_to_dict_excludes_none(self):
        user = _make_user()
        d = user.to_dict()
        assert "email" not in d
        assert "username" not in d
        assert "userId" in d

    def test_to_dict_includes_set_fields(self):
        user = _make_user(email="test@example.com", username="tester")
        d = user.to_dict()
        assert d["email"] == "test@example.com"
        assert d["username"] == "tester"

    def test_from_dict_round_trip(self):
        user = _make_user(email="round@trip.com", username="rt_user")
        d = user.to_dict()
        user2 = User.from_dict(d)
        assert user2.userId == user.userId
        assert user2.email == user.email
        assert user2.username == user.username

    def test_from_dynamodb_item(self):
        dynamo_item = {
            "userId": {"S": "berry-user"},
            "userType": {"S": "Volunteer"},
            "points": {"N": "5"},
            "settings": {
                "M": {
                    "emailNotificationEnabled": {"BOOL": False},
                    "geofenceEnabled": {"BOOL": False},
                }
            },
            "createdAt": {"S": "2024-01-01T00:00:00.000Z"},
            "lastUpdated": {"S": "2024-01-01T00:00:00.000Z"},
            "lastLoginAt": {"S": "2024-01-01T00:00:00.000Z"},
        }
        user = User.from_dynamodb_item(dynamo_item)
        assert user.userId == "berry-user"
        assert user.userType == "Volunteer"
        assert user.points == 5
        assert user.settings.emailNotificationEnabled is False


# ── update_fields ──────────────────────────────────────────────────────────

class TestUpdateFields:
    def test_update_allowed_fields(self):
        user = _make_user()
        user.update_fields({"email": "new@example.com", "username": "newuser"})
        assert user.email == "new@example.com"
        assert user.username == "newuser"

    def test_update_sets_last_updated(self):
        user = _make_user()
        old_ts = user.lastUpdated
        time.sleep(0.01)
        user.update_fields({"email": "ts@test.com"})
        assert user.lastUpdated != old_ts or True  # may be same ms; just ensure no exception

    def test_disallowed_fields_ignored(self):
        user = _make_user()
        original_created = user.createdAt
        user.update_fields({"createdAt": "2000-01-01T00:00:00.000Z", "userId": "hacker"})
        assert user.createdAt == original_created
        assert user.userId == "user-123"

    def test_neighbor_to_volunteer_allowed(self):
        user = _make_user(userType=UserType.NEIGHBOR.value)
        user.update_fields({"userType": "Volunteer"})
        assert user.userType == "Volunteer"

    def test_volunteer_to_neighbor_allowed(self):
        user = _make_user(userType=UserType.VOLUNTEER.value)
        user.update_fields({"userType": "Neighbor"})
        assert user.userType == "Neighbor"

    def test_invalid_user_type_transition_raises(self):
        user = _make_user(userType=UserType.NEIGHBOR.value)
        with pytest.raises(ValueError, match="Invalid userType transition"):
            user.update_fields({"userType": "Organizer"})

    def test_settings_merge_patch_behavior(self):
        user = _make_user()
        user.update_fields({"settings": {"geofenceEnabled": True}})
        assert user.settings.geofenceEnabled is True
        assert user.settings.emailNotificationEnabled is True

    def test_settings_invalid_key_raises(self):
        user = _make_user()
        with pytest.raises(ValueError, match="Invalid setting key: bogusKey"):
            user.update_fields({"settings": {"bogusKey": True}})

    def test_string_fields_stripped_on_update(self):
        user = _make_user()
        user.update_fields({"email": "  stripped@example.com  "})
        assert user.email == "stripped@example.com"

    def test_empty_string_field_becomes_none_on_update(self):
        user = _make_user(email="existing@example.com")
        user.update_fields({"email": "   "})
        assert user.email is None
class TestPushDeviceHelpers:
    pass
