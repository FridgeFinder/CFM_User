"""Utility helpers local to the user_devices Lambda package."""

from typing import Any, Dict


def get_authenticated_user_id(event: Dict[str, Any]) -> str:
    """Extract userId from HTTP API JWT claims."""
    return event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')
