"""
Unit tests for layers/validation_utils/python/validation_utils/validators.py
Covers: validate_username
"""
import pytest
from validation_utils.validators import validate_username, MIN_USERNAME_LENGTH, MAX_USERNAME_LENGTH


class TestValidateUsername:
    # ── None / empty → no-op ────────────────────────────────────────────────

    def test_none_is_allowed(self):
        validate_username(None)  # should not raise

    def test_empty_string_is_allowed(self):
        validate_username("")  # should not raise

    # ── too short ───────────────────────────────────────────────────────────

    def test_single_char_raises(self):
        with pytest.raises(ValueError, match="at least"):
            validate_username("a")

    def test_two_chars_raises(self):
        with pytest.raises(ValueError, match="at least"):
            validate_username("ab")

    def test_exactly_min_length_is_valid(self):
        validate_username("a" * MIN_USERNAME_LENGTH)  # should not raise

    # ── too long ────────────────────────────────────────────────────────────

    def test_over_max_length_raises(self):
        with pytest.raises(ValueError, match=str(MAX_USERNAME_LENGTH)):
            validate_username("a" * (MAX_USERNAME_LENGTH + 1))

    def test_exactly_max_length_is_valid(self):
        validate_username("a" * MAX_USERNAME_LENGTH)  # should not raise

    # ── invalid characters ──────────────────────────────────────────────────

    def test_space_raises(self):
        with pytest.raises(ValueError, match="letters, numbers, underscores"):
            validate_username("user name")

    def test_exclamation_raises(self):
        with pytest.raises(ValueError, match="letters, numbers, underscores"):
            validate_username("user!")

    def test_at_sign_raises(self):
        with pytest.raises(ValueError, match="letters, numbers, underscores"):
            validate_username("user@domain")

    def test_dot_raises(self):
        with pytest.raises(ValueError, match="letters, numbers, underscores"):
            validate_username("user.name")

    # ── valid formats ───────────────────────────────────────────────────────

    def test_alphanumeric_is_valid(self):
        validate_username("user123")  # should not raise

    def test_uppercase_is_valid(self):
        validate_username("UPPERCASE")  # should not raise

    def test_underscore_is_valid(self):
        validate_username("user_name")  # should not raise

    def test_hyphen_is_valid(self):
        validate_username("user-name")  # should not raise

    def test_mixed_valid_chars(self):
        validate_username("Mix3d_UP-low")  # should not raise
