"""User service with dummy data for development."""

import os

from server.models import UserInfo


class UserService:
    """Service for user information with dummy data."""

    def get_current_user(self) -> UserInfo:
        """Get current user information."""
        databricks_host = os.getenv('DATABRICKS_HOST')
        if databricks_host and not databricks_host.startswith('http'):
            databricks_host = f'https://{databricks_host}'

        service_principal_id = os.getenv('DATABRICKS_CLIENT_ID')

        return UserInfo(
            userName='demo_user@company.com',
            displayName='Demo User',
            databricks_host=databricks_host,
            service_principal_id=service_principal_id,
        )


# Global service instance
user_service = UserService()
