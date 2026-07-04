"""Authentication routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_client_ip, get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, PasswordChangeRequest, RefreshRequest, TokenResponse
from app.schemas.common import SuccessResponse
from app.schemas.user import UserResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate and get access tokens."""
    auth_service = AuthService(db)
    tokens = await auth_service.authenticate(data.email, data.password)

    # Audit log
    user = await auth_service.get_user_by_email(data.email)
    audit = AuditService(db)
    await audit.log(
        action="user.login",
        resource_type="user",
        resource_id=str(user.id) if user else None,
        user_id=user.id if user else None,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Refresh access token."""
    auth_service = AuthService(db)
    return await auth_service.refresh_tokens(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user profile."""
    return current_user


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    data: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change current user's password."""
    auth_service = AuthService(db)
    await auth_service.change_password(
        current_user.id, data.current_password, data.new_password
    )
    return SuccessResponse(message="Password changed successfully")
