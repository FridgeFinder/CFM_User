"""
Data access layer for user device registrations.
Stores one item per userId + installationId in a dedicated DynamoDB table.
"""
from typing import List, Optional

from dynamodb_utils import python_to_dynamodb

from user_device_models import UserDeviceRecord


class UserDeviceRepository:
    def __init__(self, dynamodb_client, table_name: str):
        self.dynamodb_client = dynamodb_client
        self.table_name = table_name

    def upsert_device(self, device: UserDeviceRecord) -> None:
        self.dynamodb_client.put_item(
            TableName=self.table_name,
            Item=python_to_dynamodb(device.to_dict()),
        )

    def get_device(self, user_id: str, installation_id: str) -> Optional[UserDeviceRecord]:
        result = self.dynamodb_client.get_item(
            TableName=self.table_name,
            Key=python_to_dynamodb({'userId': user_id, 'installationId': installation_id}),
        )
        if 'Item' not in result:
            return None
        return UserDeviceRecord.from_dynamodb_item(result['Item'])

    def list_devices_for_user(self, user_id: str) -> List[UserDeviceRecord]:
        result = self.dynamodb_client.query(
            TableName=self.table_name,
            KeyConditionExpression='userId = :user_id',
            ExpressionAttributeValues={':user_id': {'S': user_id}},
        )
        items = result.get('Items', [])
        return [UserDeviceRecord.from_dynamodb_item(item) for item in items]

    def delete_device(self, user_id: str, installation_id: str) -> None:
        self.dynamodb_client.delete_item(
            TableName=self.table_name,
            Key=python_to_dynamodb({'userId': user_id, 'installationId': installation_id}),
        )

    def find_by_token(self, token: str) -> List[UserDeviceRecord]:
        result = self.dynamodb_client.query(
            TableName=self.table_name,
            IndexName='token-index',
            KeyConditionExpression='token = :token',
            ExpressionAttributeValues={':token': {'S': token}},
        )
        items = result.get('Items', [])
        return [UserDeviceRecord.from_dynamodb_item(item) for item in items]
