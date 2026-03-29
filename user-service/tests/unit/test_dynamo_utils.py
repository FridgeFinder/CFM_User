"""
Unit tests for layers/dynamo_utils/python/dynamo_utils/client.py
Covers: get_ddb_client
"""
import pytest
from unittest.mock import patch, call
from dynamo_utils.client import get_ddb_client


class TestGetDdbClient:
    def test_returns_aws_client_when_deployment_target_is_aws(self):
        with patch("dynamo_utils.client.boto3.client") as mock_boto:
            with patch.dict("os.environ", {"DEPLOYMENT_TARGET": "aws"}):
                get_ddb_client()
        mock_boto.assert_called_once_with("dynamodb")

    def test_aws_client_has_no_endpoint_url(self):
        with patch("dynamo_utils.client.boto3.client") as mock_boto:
            with patch.dict("os.environ", {"DEPLOYMENT_TARGET": "aws"}):
                get_ddb_client()
        _, kwargs = mock_boto.call_args
        assert "endpoint_url" not in kwargs

    def test_returns_localstack_client_when_deployment_target_is_local(self):
        with patch("dynamo_utils.client.boto3.client") as mock_boto:
            with patch.dict("os.environ", {"DEPLOYMENT_TARGET": "local"}):
                get_ddb_client()
        mock_boto.assert_called_once_with("dynamodb", endpoint_url="http://localstack:4566")

    def test_returns_localstack_client_for_non_aws_value(self):
        with patch("dynamo_utils.client.boto3.client") as mock_boto:
            with patch.dict("os.environ", {"DEPLOYMENT_TARGET": "test"}):
                get_ddb_client()
        mock_boto.assert_called_once_with("dynamodb", endpoint_url="http://localstack:4566")

    def test_returns_localstack_client_when_env_var_absent(self):
        with patch("dynamo_utils.client.boto3.client") as mock_boto:
            with patch.dict("os.environ", {}, clear=True):
                get_ddb_client()
        mock_boto.assert_called_once_with("dynamodb", endpoint_url="http://localstack:4566")
