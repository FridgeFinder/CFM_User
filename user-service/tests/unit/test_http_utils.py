"""
Unit tests for layers/http_utils/python/http_utils/codes.py
             and layers/http_utils/python/http_utils/responses.py
Covers: HttpStatus, ErrorCode, http_response, error_response
"""
import json
import pytest
from http_utils.codes import HttpStatus, ErrorCode
from http_utils.responses import http_response, error_response


class TestHttpStatus:
    def test_ok_is_200(self):
        assert HttpStatus.OK == 200

    def test_created_is_201(self):
        assert HttpStatus.CREATED == 201

    def test_no_content_is_204(self):
        assert HttpStatus.NO_CONTENT == 204

    def test_bad_request_is_400(self):
        assert HttpStatus.BAD_REQUEST == 400

    def test_unauthorized_is_401(self):
        assert HttpStatus.UNAUTHORIZED == 401

    def test_forbidden_is_403(self):
        assert HttpStatus.FORBIDDEN == 403

    def test_not_found_is_404(self):
        assert HttpStatus.NOT_FOUND == 404

    def test_method_not_allowed_is_405(self):
        assert HttpStatus.METHOD_NOT_ALLOWED == 405

    def test_conflict_is_409(self):
        assert HttpStatus.CONFLICT == 409

    def test_internal_server_error_is_500(self):
        assert HttpStatus.INTERNAL_SERVER_ERROR == 500

    def test_is_int_comparable(self):
        assert HttpStatus.OK == 200
        assert HttpStatus.INTERNAL_SERVER_ERROR > HttpStatus.OK


class TestErrorCode:
    def test_values_are_strings(self):
        assert ErrorCode.USER_ID_REQUIRED == "USER_ID_REQUIRED"
        assert ErrorCode.FORBIDDEN == "FORBIDDEN"
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.ITEM_NOT_FOUND == "ITEM_NOT_FOUND"
        assert ErrorCode.ITEM_ALREADY_EXISTS == "ITEM_ALREADY_EXISTS"
        assert ErrorCode.INTERNAL_SERVER_ERROR == "INTERNAL_SERVER_ERROR"

    def test_is_str_comparable(self):
        assert ErrorCode.FORBIDDEN == "FORBIDDEN"
        assert ErrorCode.FORBIDDEN.value == "FORBIDDEN"


class TestHttpResponse:
    def test_status_code_is_set(self):
        resp = http_response(200, {"key": "val"})
        assert resp["statusCode"] == 200

    def test_body_is_json_serialized(self):
        resp = http_response(200, {"key": "val"})
        assert json.loads(resp["body"]) == {"key": "val"}

    def test_content_type_header(self):
        resp = http_response(200, {})
        assert resp["headers"]["Content-Type"] == "application/json"

    def test_no_request_id_by_default(self):
        resp = http_response(200, {})
        assert "X-Request-Id" not in resp["headers"]

    def test_request_id_added_when_provided(self):
        resp = http_response(200, {}, request_id="req-abc")
        assert resp["headers"]["X-Request-Id"] == "req-abc"

    def test_works_with_list_body(self):
        resp = http_response(200, [1, 2, 3])
        assert json.loads(resp["body"]) == [1, 2, 3]

    def test_works_with_string_body(self):
        resp = http_response(400, "bad input")
        assert json.loads(resp["body"]) == "bad input"


class TestErrorResponse:
    def test_status_code(self):
        resp = error_response(400, ErrorCode.VALIDATION_ERROR, "bad input")
        assert resp["statusCode"] == 400

    def test_error_code_in_body(self):
        resp = error_response(400, ErrorCode.VALIDATION_ERROR, "bad input")
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_message_in_body(self):
        resp = error_response(400, ErrorCode.VALIDATION_ERROR, "bad input")
        body = json.loads(resp["body"])
        assert body["error"]["message"] == "bad input"

    def test_field_omitted_when_not_provided(self):
        resp = error_response(400, ErrorCode.VALIDATION_ERROR, "bad input")
        body = json.loads(resp["body"])
        assert "field" not in body["error"]

    def test_field_included_when_provided(self):
        resp = error_response(400, ErrorCode.VALIDATION_ERROR, "too short", field="username")
        body = json.loads(resp["body"])
        assert body["error"]["field"] == "username"

    def test_request_id_propagated(self):
        resp = error_response(404, ErrorCode.ITEM_NOT_FOUND, "not found", request_id="req-xyz")
        assert resp["headers"]["X-Request-Id"] == "req-xyz"

    def test_not_found_error(self):
        resp = error_response(404, ErrorCode.ITEM_NOT_FOUND, "user not found")
        assert resp["statusCode"] == 404
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "ITEM_NOT_FOUND"

    def test_internal_server_error(self):
        resp = error_response(500, ErrorCode.INTERNAL_SERVER_ERROR, "unexpected error")
        assert resp["statusCode"] == 500
