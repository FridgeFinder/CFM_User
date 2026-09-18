"""Business logic for user-device lifecycle operations."""

from typing import Optional, Dict, Any

from http_utils import HttpStatus, http_response, error_response, ErrorCode

from user_device_models import UserDeviceRecord
from user_device_repository import UserDeviceRepository


class UserDeviceService:
    PATCHABLE_FIELDS = {
        'notificationsEnabled',
        'invalidAt',
        'lastSeenAt',
        'lastDeliveredAt',
    }

    def __init__(self, repository: UserDeviceRepository):
        self.repository = repository

    def register_device(
        self,
        user_id: str,
        installation_id: str,
        token: str,
        platform: Optional[str] = None,
        request_id: str = None,
    ) -> Dict[str, Any]:
        try:
            device = UserDeviceRecord(
                userId=user_id,
                installationId=installation_id,
                token=token,
                platform=platform,
            )
        except ValueError as e:
            return error_response(HttpStatus.BAD_REQUEST, ErrorCode.VALIDATION_ERROR, str(e), request_id=request_id)

        self.repository.upsert_device(device)
        return http_response(HttpStatus.NO_CONTENT, None, request_id)

    def get_device(
        self,
        user_id: str,
        installation_id: str,
        request_id: str = None,
    ) -> Dict[str, Any]:
        device = self.repository.get_device(user_id, installation_id)
        if device is None:
            return error_response(
                HttpStatus.NOT_FOUND,
                ErrorCode.ITEM_NOT_FOUND,
                f"Device '{installation_id}' not found for user '{user_id}'",
                request_id=request_id,
            )
        return http_response(HttpStatus.OK, {'device': device.to_dict()}, request_id)

    def update_device(
        self,
        user_id: str,
        installation_id: str,
        updates: Dict[str, Any],
        request_id: str = None,
    ) -> Dict[str, Any]:
        if not updates:
            return error_response(
                HttpStatus.BAD_REQUEST,
                ErrorCode.EMPTY_REQUEST_BODY,
                'Request body cannot be empty',
                request_id=request_id,
            )

        invalid_fields = sorted([field for field in updates.keys() if field not in self.PATCHABLE_FIELDS])
        if invalid_fields:
            return error_response(
                HttpStatus.BAD_REQUEST,
                ErrorCode.VALIDATION_ERROR,
                f"Unsupported field(s): {', '.join(invalid_fields)}",
                field=invalid_fields[0],
                request_id=request_id,
            )

        existing_device = self.repository.get_device(user_id, installation_id)
        if existing_device is None:
            return error_response(
                HttpStatus.NOT_FOUND,
                ErrorCode.ITEM_NOT_FOUND,
                f"Device '{installation_id}' not found for user '{user_id}'",
                request_id=request_id,
            )

        updated_payload = existing_device.to_dict()
        updated_payload.update(updates)

        try:
            updated_device = UserDeviceRecord(**updated_payload)
        except ValueError as e:
            return error_response(
                HttpStatus.BAD_REQUEST,
                ErrorCode.VALIDATION_ERROR,
                str(e),
                request_id=request_id,
            )

        self.repository.upsert_device(updated_device)
        return http_response(HttpStatus.OK, {'device': updated_device.to_dict()}, request_id)

    def unregister_device(
        self,
        user_id: str,
        installation_id: str,
        request_id: str = None,
    ) -> Dict[str, Any]:
        self.repository.delete_device(user_id, installation_id)
        return http_response(HttpStatus.NO_CONTENT, None, request_id)
