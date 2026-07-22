from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
from validation_utils import validate_username as _validate_username_format
from boto3.dynamodb.types import TypeDeserializer
import re

_deserializer = TypeDeserializer()


def get_utc_timestamp() -> str:
    """Generate ISO 8601 timestamp with Z suffix and milliseconds for frontend compatibility"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def clean_string_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip whitespace from all string fields and convert empty strings to None
    Used by model_validator and update_fields to ensure consistent behavior
    """
    cleaned_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            stripped = value.strip()
            cleaned_data[key] = stripped if stripped else None
        else:
            cleaned_data[key] = value
    return cleaned_data


class UserType(str, Enum):
    """
    User types for community fridge network
    Inherits from str to ensure JSON serialization compatibility
    """
    ORGANIZER = "Organizer"    # Coordinates the fridge network
    HOST = "Host"              # Hosts a fridge at their location
    VOLUNTEER = "Volunteer"    # Maintains, fills, and cleans fridges
    NEIGHBOR = "Neighbor"      # Uses the community fridges


class UserSettings(BaseModel):
    """
    Nested model for user notification and feature settings.
    Invalid keys are silently ignored on construction (extra='ignore');
    update_fields enforces strict key validation separately.
    """
    model_config = ConfigDict(extra="ignore")

    pushNotificationEnabled: bool = False
    emailNotificationEnabled: bool = True
    geofenceEnabled: bool = False


class User(BaseModel):
    """
    User model for community fridge network using Pydantic
    Provides automatic validation, serialization, and type safety
    """
    model_config = ConfigDict(
        extra="forbid",  # Reject unexpected fields (catch typos, prevent injection)
        use_enum_values=True,  # Automatically convert enums to their values in dict/json
        validate_assignment=True  # Validate when fields are updated via setattr
    )
    
    # Required fields
    userId: str
    
    # Required with default
    userType: UserType = UserType.NEIGHBOR
    points: int = 0 #TODO: Points Service?
    
    # Optional fields
    username: Optional[str] = None
    email: Optional[str] = None
    phoneNumber: Optional[str] = None
    zipcode: Optional[str] = None
    settings: UserSettings = Field(default_factory=UserSettings)
    
    # Timestamps with defaults (ISO 8601 with Z suffix for frontend compatibility)
    createdAt: str = Field(default_factory=get_utc_timestamp)
    lastUpdated: str = Field(default_factory=get_utc_timestamp)
    lastLoginAt: str = Field(default_factory=get_utc_timestamp)
    
    @model_validator(mode='before')
    @classmethod
    def strip_strings(cls, data: Any) -> Any:
        """Strip whitespace from all string fields before validation, convert empty strings to None"""
        if isinstance(data, dict):
            return clean_string_fields(data)
        return data
    
    @field_validator('userId')
    @classmethod
    def validate_user_id(cls, userId: str) -> str:
        """Validate userId is not empty"""
        if not userId:
            raise ValueError('userId is required and cannot be empty')
        return userId
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, email: Optional[str]) -> Optional[str]:
        """Validate email format if provided"""
        if email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise ValueError('Invalid email format')
        return email
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, username: Optional[str]) -> Optional[str]:
        """Validate username format if provided"""
        _validate_username_format(username)
        return username
    
    @field_validator('phoneNumber')
    @classmethod
    def validate_phone_number(cls, phoneNumber: Optional[str]) -> Optional[str]:
        """Validate phone number format if provided"""
        MIN_PHONE_LENGTH = 10
        MAX_PHONE_LENGTH = 15
        if phoneNumber:
            # Remove common separators for validation
            digits_only = re.sub(r'[\s\-\(\)\+\.]', '', phoneNumber)
            if not digits_only.isdigit():
                raise ValueError('Phone number can only contain digits and separators (spaces, hyphens, parentheses, plus)')
            if len(digits_only) < MIN_PHONE_LENGTH:
                raise ValueError(f'Phone number must have at least {MIN_PHONE_LENGTH} digits')
            if len(digits_only) > MAX_PHONE_LENGTH:
                raise ValueError(f'Phone number must have at most {MAX_PHONE_LENGTH} digits')
            return digits_only
        return phoneNumber
    
    @field_validator('zipcode')
    @classmethod
    def validate_zipcode(cls, zipcode: Optional[str]) -> Optional[str]:
        """Validate zipcode format if provided"""
        MIN_ZIPCODE_LENGTH = 3
        MAX_ZIPCODE_LENGTH = 10
        if zipcode:
            if len(zipcode) < MIN_ZIPCODE_LENGTH:
                raise ValueError(f'Zipcode must be at least {MIN_ZIPCODE_LENGTH} characters')
            if len(zipcode) > MAX_ZIPCODE_LENGTH:
                raise ValueError(f'Zipcode must be {MAX_ZIPCODE_LENGTH} characters or less')
            # Only allow alphanumeric, spaces, hyphens for international support
            if not re.match(r'^[a-zA-Z0-9\s\-]+$', zipcode):
                raise ValueError('Zipcode must contain only letters, numbers, spaces, and hyphens')
        return zipcode
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create a User instance from a dictionary
        Pydantic handles validation automatically
        """
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert User instance to dictionary format
        Uses Pydantic's model_dump with enum values as strings
        Excludes None values to save space
        """
        return self.model_dump(mode='json', exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'User':
        """
        Create a User from a DynamoDB Item (AttributeValue map).
        Decodes AttributeValues to Python primitives using boto3's TypeDeserializer,
        then delegates to from_dict.
        """
        python_item = {k: _deserializer.deserialize(v) for k, v in item.items()}
        return cls.from_dict(python_item)
    
    def update_fields(self, updates: Dict[str, Any]) -> None:
        """
        Update user fields from a dictionary
        Only updates allowed fields and re-validates
        Special handling for userType: only NEIGHBOR → VOLUNTEER is allowed
        """
        # Strip strings and convert empty strings to None (same as model_validator)
        cleaned_updates = clean_string_fields(updates)
        
        # Handle userType transition validation
        if 'userType' in cleaned_updates:
            new_type = cleaned_updates['userType']
            # Only allow transitions to NEIGHBOR or VOLUNTEER for now
            #TODO: update this after discussion on what user types should do
            if new_type == UserType.NEIGHBOR.value or new_type == UserType.VOLUNTEER.value:
                self.userType = new_type
            elif self.userType == new_type:
                pass  # No change
            else:
                raise ValueError(
                    f"Invalid userType transition. Users can only change to {UserType.NEIGHBOR.value} or {UserType.VOLUNTEER.value} via self-update."
                )
            # Remove from cleaned_updates dict so it's not processed again below
            del cleaned_updates['userType']
        
        # Validate and merge settings if settings are being updated (PATCH semantics)
        if 'settings' in cleaned_updates:
            for key in cleaned_updates['settings']:
                if key not in UserSettings.model_fields:
                    raise ValueError(f"Invalid setting key: {key}")

            # Merge new settings with existing settings (PATCH behavior)
            # Only update the keys that are provided, keep existing values for others
            cleaned_updates['settings'] = self.settings.model_copy(update=cleaned_updates['settings'])
        
        # Fields that can be updated (excluding userType - handled above)
        allowed_fields = {
            'email', 'phoneNumber', 'username', 'points',
            'zipcode', 'lastLoginAt', 'settings'
        }
        
        # Apply updates
        for field_name, value in cleaned_updates.items():
            if field_name in allowed_fields:
                setattr(self, field_name, value)
        
        # Always update lastUpdated when update_fields is called
        self.lastUpdated = get_utc_timestamp()
        
        # Pydantic automatically validates fields on assignment
    
    def __str__(self) -> str:
        return self.model_dump_json(indent=2)

