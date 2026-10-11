"""Auth API endpoints — register, login, token refresh, OTP flows."""

from vayuapi import VayuAPI, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from services.auth import AuthService
from schemas.user import (
    UserRegisterSchema, UserLoginSchema, TokenRefreshSchema,
    PasswordResetRequestSchema, OTPVerifySchema, EmailVerifySchema,
)

router = VayuAPI()


@router.post("/api/auth/register")
async def register(data: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    user = await svc.register(data)
    return {"message": "Registration successful. Please verify your email.", "user_id": user.id}


@router.post("/api/auth/login")
async def login(data: UserLoginSchema, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    return await svc.login(data)


@router.post("/api/auth/refresh")
async def refresh(data: TokenRefreshSchema, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    return await svc.refresh_tokens(data.refresh_token)


@router.post("/api/auth/verify-email")
async def verify_email(data: EmailVerifySchema, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    await svc.verify_email(data.email, data.otp_code)
    return {"message": "Email verified successfully"}


@router.post("/api/auth/forgot-password")
async def forgot_password(data: PasswordResetRequestSchema, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    await svc.request_password_reset(data.email)
    return {"message": "OTP sent to your email if account exists"}


@router.post("/api/auth/reset-password")
async def reset_password(data: OTPVerifySchema, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    await svc.reset_password_with_otp(data.email, data.otp_code, data.new_password)
    return {"message": "Password reset successfully"}
