import os
import boto3


def get_ddb_client():
    """
    Return a DynamoDB client pointed at AWS or LocalStack depending on
    the DEPLOYMENT_TARGET environment variable (default: aws).
    """
    if os.getenv("DEPLOYMENT_TARGET", "local") == "aws":
        return boto3.client("dynamodb")
    return boto3.client("dynamodb", endpoint_url="http://localstack:4566")
