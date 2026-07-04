"""Authentication and user management service."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate, UserUpdate


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, email: str, password: str) -> TokenResponse:
        user = await self.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()

        token_data = {"sub": str(user.id), "email": user.email, "is_admin": user.is_admin}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")

        user = await self.get_user_by_id(uuid.UUID(payload["sub"]))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        token_data = {"sub": str(user.id), "email": user.email, "is_admin": user.is_admin}
        new_access = create_access_token(token_data)
        new_refresh = create_refresh_token(token_data)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(self, data: UserCreate) -> User:
        existing = await self.get_user_by_email(data.email)
        if existing:
            raise AuthenticationError(f"User with email {data.email} already exists")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            is_admin=data.is_admin,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        return user

    async def delete_user(self, user_id: uuid.UUID) -> None:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        await self.db.delete(user)
        await self.db.flush()

    async def list_users(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[User], int]:
        count_result = await self.db.execute(select(func.count(User.id)))
        total = count_result.scalar()

        result = await self.db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        users = list(result.scalars().all())
        return users, total

    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        await self.db.flush()

    async def ensure_admin_exists(self) -> None:
        admin = await self.get_user_by_email(settings.ADMIN_EMAIL)
        if not admin:
            admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                full_name=settings.ADMIN_FULL_NAME,
                is_admin=True,
            )
            self.db.add(admin)
            await self.db.commit()
