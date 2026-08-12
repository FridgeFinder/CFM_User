"""
Unit tests for functions/hello_world/hello_world_handler.py
"""
import json
import hello_world_handler


class TestHelloWorldLambdaHandler:
    def test_returns_200(self):
        result = hello_world_handler.lambda_handler({}, None)
        assert result["statusCode"] == 200

    def test_body_contains_message(self):
        result = hello_world_handler.lambda_handler({}, None)
        body = json.loads(result["body"])
        assert body["message"] == "hello user service"

