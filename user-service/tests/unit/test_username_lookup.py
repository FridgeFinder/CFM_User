"""Unit tests for the public username lookup Lambda."""
import json
from unittest.mock import MagicMock, patch

from http_utils import HttpStatus
import username_lookup_handler as app


def _make_context(request_id='req-username-lookup'):
    context = MagicMock()
    context.aws_request_id = request_id
    return context


def _make_event(user_id='u-1'):
    return {'pathParameters': {'userId': user_id} if user_id else {}}


class TestGetUsername:
    def test_returns_username_when_user_exists(self):
        with patch.object(app, 'dynamodb_client') as mock_ddb:
            mock_ddb.get_item.return_value = {'Item': {'username': {'S': 'riverstone'}}}

            result = app.get_username('u-1')

        assert result == 'riverstone'
        kwargs = mock_ddb.get_item.call_args.kwargs
        assert kwargs['Key'] == {'userId': {'S': 'u-1'}}
        assert kwargs['ProjectionExpression'] == 'username'

    def test_returns_none_when_user_or_username_is_missing(self):
        with patch.object(app, 'dynamodb_client') as mock_ddb:
            mock_ddb.get_item.return_value = {}
            assert app.get_username('u-1') is None

            mock_ddb.get_item.return_value = {'Item': {}}
            assert app.get_username('u-1') is None


class TestLambdaHandler:
    def test_returns_400_when_user_id_is_missing(self):
        result = app.lambda_handler(_make_event(None), _make_context())

        assert result['statusCode'] == HttpStatus.BAD_REQUEST

    def test_returns_username_when_user_is_found(self):
        with patch.object(app, 'dynamodb_client') as mock_ddb:
            mock_ddb.get_item.return_value = {'Item': {'username': {'S': 'riverstone'}}}
            result = app.lambda_handler(_make_event(), _make_context('req-42'))

        assert result['statusCode'] == HttpStatus.OK
        assert result['headers']['X-Request-Id'] == 'req-42'
        assert json.loads(result['body']) == {'username': 'riverstone'}

    def test_returns_404_when_user_is_missing(self):
        with patch.object(app, 'dynamodb_client') as mock_ddb:
            mock_ddb.get_item.return_value = {}
            result = app.lambda_handler(_make_event(), _make_context())

        assert result['statusCode'] == HttpStatus.NOT_FOUND

    def test_returns_500_when_dynamodb_fails(self):
        with patch.object(app, 'dynamodb_client') as mock_ddb:
            mock_ddb.get_item.side_effect = RuntimeError('DynamoDB unavailable')
            result = app.lambda_handler(_make_event(), _make_context())

        assert result['statusCode'] == HttpStatus.INTERNAL_SERVER_ERROR