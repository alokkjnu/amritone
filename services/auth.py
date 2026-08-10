"""Authentication and user service."""

from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from models.user import User
from models.otp import OTPPurpose
from repositories.user import UserRepository, RoleRepository
from schemas.user import UserRegisterSchema, UserLoginSchema
from utils.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from utils.otp import generate_otp
from utils.email import send_email
from vayuapi import HTTPException

logger = logging.getLogger(__name__)


class AuthService:
    """Handles registration, login, token management, and password reset."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)

    async def register(self, data: UserRegisterSchema) -> User:
        """Register a new customer account."""
        if await self.user_repo.get_by_email(data.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        if data.phone and await self.user_repo.get_by_phone(data.phone):
            raise HTTPException(status_code=400, detail="Phone number already registered")

        customer_role = await self.role_repo.get_by_name("customer")

        user = await self.user_repo.create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            is_active=True,
            is_verified=False,
        )

        if customer_role:
            from models.user import UserRole
            self.session.add(UserRole(user_id=user.id, role_id=customer_role.id))
            await self.session.flush()

        await self._send_verification_otp(user)
        logger.info("New user registered: %s (id=%d)", user.email, user.id)
        return user

    async def login(self, data: UserLoginSchema) -> dict:
        """Authenticate user and return token pair."""
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")

        # Update last_login
        await self.user_repo.update(user, last_login=datetime.now(timezone.utc))

        _staff_roles = {"super_admin", "admin", "inventory_manager", "order_manager", "customer_support"}
        is_staff = bool(user.role_names & _staff_roles)

        token_data = {"sub": str(user.id), "email": user.email}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "token_type": "bearer",
            "is_staff": is_staff,
        }

    async def refresh_tokens(self, refresh_token: str) -> dict:
        """Rotate refresh token and return new pair."""
        from jose import JWTError
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        user = await self.user_repo.get_by_id(int(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        token_data = {"sub": str(user.id), "email": user.email}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "token_type": "bearer",
        }

    async def request_password_reset(self, email: str) -> None:
        """Send OTP for password reset."""
        user = await self.user_repo.get_by_email(email)
        if user:
            await self._send_otp(user, "password_reset")

    async def reset_password_with_otp(self, email: str, otp_code: str, new_password: str) -> None:
        """Verify OTP and update password."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await self._verify_otp(user, otp_code, "password_reset")
        await self.user_repo.update(user, password_hash=hash_password(new_password))
        logger.info("Password reset for user %s", email)

    async def verify_email(self, email: str, otp_code: str) -> None:
        """Verify email with OTP."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Email already verified")

        await self._verify_otp(user, otp_code, "email_verify")
        await self.user_repo.update(user, is_verified=True)

    async def _send_verification_otp(self, user: User) -> None:
        await self._send_otp(user, "email_verify")

    async def _send_otp(self, user: User, purpose: str) -> None:
        from models.otp import OTPToken, OTPPurpose
        otp = generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        self.session.add(OTPToken(
            user_id=user.id,
            otp_code=otp,
            purpose=OTPPurpose(purpose),
            expires_at=expires_at,
        ))
        await self.session.flush()

        subject_map = {
            "email_verify": f"Verify Your Email — {settings.APP_NAME}",
            "password_reset": f"Password Reset OTP — {settings.APP_NAME}",
        }
        body = f"""
        <h2>Hello {user.first_name},</h2>
        <p>Your OTP is: <strong style="font-size:24px;">{otp}</strong></p>
        <p>This OTP expires in {settings.OTP_EXPIRY_MINUTES} minutes.</p>
        <p>If you did not request this, please ignore this email.</p>
        """
        await send_email(user.email, subject_map.get(purpose, "OTP"), body)

    async def _verify_otp(self, user: User, otp_code: str, purpose: str) -> None:
        from models.otp import OTPToken, OTPPurpose
        from sqlalchemy import select
        stmt = (
            select(OTPToken)
            .where(
                OTPToken.user_id == user.id,
                OTPToken.otp_code == otp_code,
                OTPToken.purpose == OTPPurpose(purpose),
                OTPToken.is_used == False,
                OTPToken.expires_at > datetime.now(timezone.utc),
            )
            .order_by(OTPToken.created_at.desc())
            .limit(1)
        )
        token = (await self.session.execute(stmt)).scalar_one_or_none()
        if not token:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        token.is_used = True
        self.session.add(token)
        await self.session.flush()
