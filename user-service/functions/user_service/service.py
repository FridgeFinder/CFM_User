"""
Service layer for user operations
Handles business logic and validation
"""
import logging
import json
from typing import Dict, Any
from botocore.exceptions import ClientError
from models import User, UserType
from repository import UserRepository
from utils import response, error_response, ErrorCode

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class UserService:
    """
    User service for managing user operations
    Encapsulates business logic and validation
    """
    
    def __init__(self, repository: UserRepository):
        """
        Initialize UserService with repository dependency
        
        Args:
            repository: UserRepository instance for data access
        """
        self.repository = repository
    
    def create_user(self, body: Dict[str, Any], request_id: str = None) -> Dict[str, Any]:
        """
        Create a new user
        Args:
            body: Request body with user data
            request_id: Optional request ID for tracing 
        Returns:
            API response with created user or error
        """
        
        # Validate with Pydantic model
        try:
            user = User(**body)
        except ValueError as e:
            return error_response(400, ErrorCode.VALIDATION_ERROR, str(e))
        
        # Save to database
        try:
            self.repository.create_user(user.to_dict())
            logger.info('User created successfully',
                       extra={'operation': 'create_user',
                              'user_id': user.userId,
                              'request_id': request_id})
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return error_response(409, ErrorCode.USER_ALREADY_EXISTS, 
                                    'User with this userId already exists',
                                    log_level='warning',
                                    request_id=request_id,
                                    extra={'operation': 'create_user',
                                           'user_id': user.userId})
            raise
        
        return response(201, {'user': user.model_dump(mode='json')}, request_id)
    
    def get_user(self, user_id: str, request_id: str = None) -> Dict[str, Any]:
        """
        Get a user by ID
        
        Args:
            user_id: User ID to retrieve
            request_id: Optional request ID for tracing
            
        Returns:
            API response with user data or error
        """
        # Fetch from database
        user = self.repository.get_user_by_id(user_id)
        if not user:
            return error_response(404, ErrorCode.USER_NOT_FOUND, 
                                f"User not found",
                                log_level='info',
                                request_id=request_id,
                                extra={'operation': 'get_user',
                                       'user_id': user_id})
        
        return response(200, {'user': user.model_dump(mode='json')}, request_id)
    
    def update_user(self, user_id: str, updates: Dict[str, Any], request_id: str = None) -> Dict[str, Any]:
        """
        Update a user
        
        Args:
            user_id: User ID to update
            updates: Fields to update
            request_id: Optional request ID for tracing
            
        Returns:
            API response with updated user or error
        """
        # Validate request body is not empty
        if not updates:
            return error_response(400, ErrorCode.EMPTY_REQUEST_BODY, 'Request body cannot be empty')
        
        # Check if user exists
        user = self.repository.get_user_by_id(user_id)
        if not user:
            return error_response(404, ErrorCode.USER_NOT_FOUND, 
                                f"User with userId '{user_id}' not found",
                                log_level='info',
                                request_id=request_id,
                                extra={'operation': 'update_user',
                                       'user_id': user_id})
        
        # Apply updates with validation
        try:
            user.update_fields(updates)
        except ValueError as e:
            return error_response(400, ErrorCode.VALIDATION_ERROR, str(e))
        
        # Save to database
        self.repository.update_user(user.to_dict())        
        return response(200, {'user': user.model_dump(mode='json')}, request_id)
    
    def delete_user(self, user_id: str, request_id: str = None) -> Dict[str, Any]:
        """
        Delete a user
        Args:
            user_id: User ID to delete
            request_id: Optional request ID for tracing
        Returns:
            API response with success message or error
        """
        # Check if user exists
        user = self.repository.get_user_by_id(user_id)
        if not user:
            return error_response(404, ErrorCode.USER_NOT_FOUND, f"User not found")
        
        # Delete from database
        self.repository.delete_user(user_id)        
        return response(204, None, request_id)
