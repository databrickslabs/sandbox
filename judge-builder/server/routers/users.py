"""Users API router."""

from fastapi import APIRouter

from server.models import UserInfo
from server.services.user_service import user_service

router = APIRouter()


@router.get('/me', response_model=UserInfo)
async def get_current_user():
    """Get current user information."""
    return user_service.get_current_user()
