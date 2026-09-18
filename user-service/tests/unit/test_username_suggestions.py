"""Unit tests for functions/username_suggestions/username_suggestions_handler.py."""
import json
from unittest.mock import MagicMock, patch

import pytest

from http_utils import HttpStatus
import username_suggestions_handler as app


class TestUsernameAvailabilityRepository:
    def test_is_username_available_true_when_count_zero(self):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {'Count': 0}
        repo = app.UsernameAvailabilityRepository(mock_ddb, 'users-test')

        result = repo.is_username_available('free_name')

        assert result is True
        mock_ddb.query.assert_called_once()

    def test_is_username_available_false_when_count_nonzero(self):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {'Count': 1}
        repo = app.UsernameAvailabilityRepository(mock_ddb, 'users-test')

        result = repo.is_username_available('taken_name')

        assert result is False


class TestParseCount:
    def test_defaults_to_one_when_missing(self):
        assert app._parse_count({}) == 1

    def test_accepts_valid_count(self):
        assert app._parse_count({'queryStringParameters': {'count': '20'}}) == 20

    @pytest.mark.parametrize('raw', ['0', '-1', '21'])
    def test_rejects_out_of_range(self, raw):
        with pytest.raises(ValueError, match='between 1 and 20'):
            app._parse_count({'queryStringParameters': {'count': raw}})

    def test_rejects_non_integer(self):
        with pytest.raises(ValueError, match='integer'):
            app._parse_count({'queryStringParameters': {'count': 'abc'}})


class _AlwaysFailGenerator:
    def __init__(self):
        self.calls = 0

    def generate_unique_username(self, max_attempts):
        self.calls += 1
        raise RuntimeError('no candidate')


class TestGenerateSuggestions:
    def test_enforces_total_attempt_capacity(self):
        generator = _AlwaysFailGenerator()

        with pytest.raises(RuntimeError, match='Unable to generate requested'):
            app._generate_suggestions(generator, count=1, max_calls=3, per_username_attempts=1)

        assert generator.calls == 3

    def test_removes_duplicates_in_same_response(self):
        generator = MagicMock()
        generator.generate_unique_username.side_effect = ['Same-0001', 'Same-0001', 'Other-0002']

        result = app._generate_suggestions(generator, count=2, max_calls=5, per_username_attempts=1)

        assert result == ['Same-0001', 'Other-0002']


class TestLambdaHandler:
    def _make_context(self, request_id='req-suggestions'):
        ctx = MagicMock()
        ctx.aws_request_id = request_id
        return ctx

    def test_returns_400_for_invalid_count(self):
        result = app.lambda_handler({'queryStringParameters': {'count': '21'}}, self._make_context())

        assert result['statusCode'] == HttpStatus.BAD_REQUEST
        body = json.loads(result['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert body['error']['field'] == 'count'

    def test_returns_200_with_requested_suggestions(self):
        with patch.object(app, 'dynamodb_client') as mock_ddb:
            mock_ddb.query.return_value = {'Count': 0}
            with patch('username_utils.username_generator.random.choice', side_effect=['Active', 'Apple', '1', '2', '3', '4']):
                result = app.lambda_handler({'queryStringParameters': {'count': '1'}}, self._make_context('req-42'))

        assert result['statusCode'] == HttpStatus.OK
        assert result['headers']['X-Request-Id'] == 'req-42'
        body = json.loads(result['body'])
        assert body['count'] == 1
        assert body['suggestions'] == ['ActiveApple-1234']

    def test_returns_500_when_generation_exhausted(self):
        with patch.object(app, '_generate_suggestions', side_effect=RuntimeError('exhausted')):
            result = app.lambda_handler({'queryStringParameters': {'count': '2'}}, self._make_context())

        assert result['statusCode'] == HttpStatus.INTERNAL_SERVER_ERROR
        body = json.loads(result['body'])
        assert body['error']['code'] == 'INTERNAL_SERVER_ERROR'
