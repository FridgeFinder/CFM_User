import re
from typing import Optional


MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30


def validate_username(username: Optional[str]) -> None:
    """
    Validate username format if provided.

    Args:
        username: The username string to validate.

    Raises:
        ValueError: If the username is present but invalid.
    """
    if username:
        if len(username) < MIN_USERNAME_LENGTH:
            raise ValueError(f'Username must be at least {MIN_USERNAME_LENGTH} characters')
        if len(username) > MAX_USERNAME_LENGTH:
            raise ValueError(f'Username must be {MAX_USERNAME_LENGTH} characters or less')
        # Allow alphanumeric, underscore, and hyphen only (no spaces)
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
