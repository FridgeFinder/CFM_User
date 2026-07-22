"""
User device record model for the dedicated user_devices table.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from boto3.dynamodb.types import TypeDeserializer
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_deserializer = TypeDeserializer()


def get_utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def clean_string_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            stripped = value.strip()
            cleaned_data[key] = stripped if stripped else None
        else:
            cleaned_data[key] = value
    return cleaned_data


class UserDeviceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    userId: str
    installationId: str
    token: str
    platform: Optional[str] = None
    notificationsEnabled: bool = True
    createdAt: str = Field(default_factory=get_utc_timestamp)
    lastSeenAt: str = Field(default_factory=get_utc_timestamp)
    lastDeliveredAt: Optional[str] = None
    invalidAt: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def strip_strings(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return clean_string_fields(data)
        return data

    @field_validator('userId', 'installationId', 'token')
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError('Value is required and cannot be empty')
        return value

    @field_validator('platform')
    @classmethod
    def validate_platform(cls, platform: Optional[str]) -> Optional[str]:
        if platform is None:
            return platform
        platform = platform.lower()
        if platform not in {'ios', 'android', 'web', 'unknown'}:
            raise ValueError('platform must be one of: ios, android, web, unknown')
        return platform

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserDeviceRecord':
        return cls(**data)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'UserDeviceRecord':
        python_item = {k: _deserializer.deserialize(v) for k, v in item.items()}
        return cls.from_dict(python_item)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode='json', exclude_none=True)
