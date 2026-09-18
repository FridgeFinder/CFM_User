"""Lambda handler for username suggestion generation."""
import os
import logging
from typing import Any, Dict, List, Optional, Set

from http_utils import HttpStatus, ErrorCode, http_response, error_response
from dynamo_utils import get_ddb_client
from username_utils import UsernameGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_COUNT = 20
DEFAULT_COUNT = 1
MAX_PER_USERNAME_ATTEMPTS = 10
MAX_TOTAL_GENERATION_CALLS = 200


dynamodb_client = get_ddb_client()
table_name = os.environ['USERS_TABLE']


class UsernameAvailabilityRepository:
    """Minimal repository used by UsernameGenerator for availability checks."""

    def __init__(self, dynamodb_client, users_table: str):
        self.dynamodb_client = dynamodb_client
        self.users_table = users_table

    def is_username_available(self, username: str) -> bool:
        result = self.dynamodb_client.query(
            TableName=self.users_table,
            IndexName='username-index',
            KeyConditionExpression='username = :username',
            ExpressionAttributeValues={':username': {'S': username}},
            Limit=1,
            Select='COUNT',
        )
        return result.get('Count', 0) == 0


def _parse_count(event: Dict[str, Any]) -> int:
    params = event.get('queryStringParameters') or {}
    raw_count = params.get('count')
    if raw_count is None:
        return DEFAULT_COUNT

    try:
        count = int(raw_count)
    except (TypeError, ValueError) as exc:
        raise ValueError('count must be an integer between 1 and 20') from exc

    if count < 1 or count > MAX_COUNT:
        raise ValueError('count must be between 1 and 20')
    return count


def _generate_suggestions(
    generator: UsernameGenerator,
    count: int,
    max_calls: int = MAX_TOTAL_GENERATION_CALLS,
    per_username_attempts: int = MAX_PER_USERNAME_ATTEMPTS,
) -> List[str]:
    suggestions: List[str] = []
    seen: Set[str] = set()
    calls = 0

    while len(suggestions) < count and calls < max_calls:
        calls += 1
        try:
            candidate = generator.generate_unique_username(max_attempts=per_username_attempts)
        except RuntimeError:
            continue

        if candidate in seen:
            continue

        seen.add(candidate)
        suggestions.append(candidate)

    if len(suggestions) < count:
        raise RuntimeError('Unable to generate requested number of username suggestions')

    return suggestions


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    request_id = context.aws_request_id if context else 'unknown'

    try:
        count = _parse_count(event)
    except ValueError as exc:
        return error_response(
            HttpStatus.BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            str(exc),
            field='count',
            request_id=request_id,
        )

    repository = UsernameAvailabilityRepository(dynamodb_client, table_name)
    generator = UsernameGenerator(repository)

    try:
        suggestions = _generate_suggestions(generator, count)
        return http_response(
            HttpStatus.OK,
            {'suggestions': suggestions, 'count': len(suggestions)},
            request_id,
        )
    except Exception as exc:
        logger.exception(
            'Error generating username suggestions',
            extra={
                'request_id': request_id,
                'requested_count': count,
                'error_message': str(exc),
                'error_type': type(exc).__name__,
            },
        )
        return error_response(
            HttpStatus.INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            'Unable to generate username suggestions, please try again',
            request_id=request_id,
        )
