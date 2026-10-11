"""Pydantic schemas for User, Auth, and Address."""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegisterSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,15}$")
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshSchema(BaseModel):
    refresh_token: str


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class EmailVerifySchema(BaseModel):
    email: EmailStr
    otp_code: str


class UserProfileUpdateSchema(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,15}$")
    newsletter_subscribed: Optional[bool] = None


class UserResponseSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    is_active: bool
    is_verified: bool
    avatar: Optional[str]
    newsletter_subscribed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AddressCreateSchema(BaseModel):
    label: str = Field("Home", max_length=50)
    full_name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    address_line1: str = Field(..., min_length=5, max_length=500)
    address_line2: Optional[str] = Field(None, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., pattern=r"^[0-9]{6}$")
    country: str = Field("India", max_length=100)
    is_default: bool = False


class AddressResponseSchema(BaseModel):
    id: int
    label: str
    full_name: str
    phone: str
    address_line1: str
    address_line2: Optional[str]
    city: str
    state: str
    pincode: str
    country: str
    is_default: bool

    model_config = {"from_attributes": True}
