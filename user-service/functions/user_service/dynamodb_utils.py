"""
DynamoDB utilities for converting Python types to DynamoDB format
"""
from typing import Any, Dict
from boto3.dynamodb.types import TypeSerializer


# Initialize serializer
serializer = TypeSerializer()


def python_to_dynamodb(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Python dict to DynamoDB AttributeValue map
    Example: {'userId': 'abc', 'age': 25} -> {'userId': {'S': 'abc'}, 'age': {'N': '25'}}
    """
    return {k: serializer.serialize(v) for k, v in item.items()}
