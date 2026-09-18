"""DynamoDB serialization helpers local to the user_devices Lambda package."""

from typing import Any, Dict
from boto3.dynamodb.types import TypeSerializer

serializer = TypeSerializer()


def python_to_dynamodb(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Python dict to DynamoDB AttributeValue map."""
    return {k: serializer.serialize(v) for k, v in item.items()}
