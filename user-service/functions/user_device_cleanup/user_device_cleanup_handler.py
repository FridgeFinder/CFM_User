"""Delete user device rows when a User Deleted event is received."""
import logging
import os
from typing import Any, Dict, List

from dynamo_utils import get_ddb_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


dynamodb = get_ddb_client()
USER_DEVICES_TABLE = os.environ['USER_DEVICES_TABLE']


def _chunk(items: List[Dict[str, Dict[str, str]]], size: int) -> List[List[Dict[str, Dict[str, str]]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _query_device_keys(user_id: str) -> List[Dict[str, Dict[str, str]]]:
    keys: List[Dict[str, Dict[str, str]]] = []
    exclusive_start_key = None

    while True:
        query_kwargs = {
            'TableName': USER_DEVICES_TABLE,
            'KeyConditionExpression': 'userId = :user_id',
            'ExpressionAttributeValues': {':user_id': {'S': user_id}},
            'ProjectionExpression': 'userId, installationId',
        }
        if exclusive_start_key:
            query_kwargs['ExclusiveStartKey'] = exclusive_start_key

        response = dynamodb.query(**query_kwargs)
        for item in response.get('Items', []):
            keys.append(
                {
                    'userId': item['userId'],
                    'installationId': item['installationId'],
                }
            )

        exclusive_start_key = response.get('LastEvaluatedKey')
        if not exclusive_start_key:
            break

    return keys


def _delete_keys(keys: List[Dict[str, Dict[str, str]]]) -> int:
    if not keys:
        return 0

    deleted_count = 0
    for batch in _chunk(keys, 25):
        request_items = {
            USER_DEVICES_TABLE: [
                {'DeleteRequest': {'Key': key}}
                for key in batch
            ]
        }

        while request_items.get(USER_DEVICES_TABLE):
            response = dynamodb.batch_write_item(RequestItems=request_items)
            unprocessed = response.get('UnprocessedItems', {})
            request_items = unprocessed

        deleted_count += len(batch)

    return deleted_count


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    request_id = context.aws_request_id if context else 'unknown'
    detail = event.get('detail') or {}
    user_id = detail.get('userId')

    if not user_id:
        logger.warning(
            'Skipping event without userId',
            extra={'request_id': request_id, 'event': event},
        )
        return {'status': 'ignored', 'reason': 'missing_user_id'}

    keys = _query_device_keys(user_id)
    deleted_count = _delete_keys(keys)

    logger.info(
        'Deleted user device rows',
        extra={
            'request_id': request_id,
            'user_id': user_id,
            'deleted_count': deleted_count,
        },
    )
    return {'status': 'deleted', 'userId': user_id, 'deletedCount': deleted_count}
