"""
Utility functions for API responses and JWT handling
"""
from typing import Dict, Any

def get_authenticated_user_id(event: Dict[str, Any]) -> str:
    """
    Extract userId from JWT token claims
    API Gateway v2 (HTTP API) provides JWT claims in requestContext.authorizer.jwt.claims
    Args:
        event: API Gateway HTTP API event
    Returns:
        User ID from JWT 'sub' claim
    """
    # For HTTP API, JWT claims are in requestContext.authorizer.jwt.claims
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')

    return user_id

