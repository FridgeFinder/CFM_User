"""
Unit tests for functions/user_service/username_generator.py
"""
from unittest.mock import MagicMock, patch
import pytest

from username_utils import UsernameGenerator


def _make_generator():
    repo = MagicMock()
    return repo, UsernameGenerator(repo)


class TestUsernameGenerator:
    def test_returns_first_available_candidate(self):
        repo, generator = _make_generator()
        repo.is_username_available.return_value = True

        with patch(
            'username_utils.username_generator.random.choice',
            side_effect=['Active', 'Apple', 'A', 'B', 'C', 'D'],
        ):
            username = generator.generate_unique_username(max_attempts=1)

        assert username == 'ActiveApple-ABCD'
        repo.is_username_available.assert_called_once_with('ActiveApple-ABCD')

    def test_uses_fallback_suffix_length_after_initial_attempts(self):
        repo, generator = _make_generator()
        repo.is_username_available.side_effect = [False, True]

        with patch(
            'username_utils.username_generator.random.choice',
            side_effect=[
                'Active', 'Apple', 'A', 'B', 'C', 'D',
                'Brave', 'Berry', '1', '2', '3', '4', '5', '6',
            ],
        ):
            username = generator.generate_unique_username(max_attempts=1)

        assert username == 'BraveBerry-123456'
        assert repo.is_username_available.call_count == 2

    def test_raises_when_no_available_username_found(self):
        repo, generator = _make_generator()
        repo.is_username_available.return_value = False

        with patch('username_utils.username_generator.random.choice', return_value='A'):
            with pytest.raises(RuntimeError, match='Unable to generate an available username'):
                generator.generate_unique_username(max_attempts=1)
