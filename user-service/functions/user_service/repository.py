"""
Data access layer for User service
Handles all DynamoDB operations
"""
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from dynamodb_utils import python_to_dynamodb
from models import User


class UserRepository:
    """Repository for user data access operations"""
    
    def __init__(self, dynamodb_client, table_name: str):
        self.dynamodb_client = dynamodb_client
        self.table_name = table_name
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by userId
        Args:
            user_id: The userId to lookup
        Returns:
            User model instance, or None if not found
        """
        result = self.dynamodb_client.get_item(
            TableName=self.table_name,
            Key=python_to_dynamodb({'userId': user_id})
        )
        
        if 'Item' not in result:
            return None
        
        # Construct domain model from raw DynamoDB item; errors propagate to service layer
        return User.from_dynamodb_item(result['Item'])
    
    def create_user(self, user_data: Dict[str, Any]) -> None:
        """
        Create a new user record
        
        Args:
            user_data: User data to insert
            
        Raises:
            ClientError: If user already exists (ConditionalCheckFailedException)
        """
        self.dynamodb_client.put_item(
            TableName=self.table_name,
            Item=python_to_dynamodb(user_data),
            ConditionExpression='attribute_not_exists(userId)'
        )
    
    def update_user(self, user_data: Dict[str, Any]) -> None:
        """
        Update an existing user record
        
        Args:
            user_data: Complete user data to save
        """
        self.dynamodb_client.put_item(
            TableName=self.table_name,
            Item=python_to_dynamodb(user_data)
        )
    
    def user_exists(self, user_id: str) -> bool:
        """
        Check if a user exists
        
        Args:
            user_id: The userId to check
            
        Returns:
            True if user exists, False otherwise
        """
        return self.get_user_by_id(user_id) is not None
    
    def delete_user(self, user_id: str) -> None:
        """
        Delete a user record
        
        Args:
            user_id: The userId to delete
        """
        self.dynamodb_client.delete_item(
            TableName=self.table_name,
            Key=python_to_dynamodb({'userId': user_id})
        )
