"""
JWT authentication dependency for VayuAPI.
Provides get_current_user and require_roles helpers.
"""

from __future__ import annotations
import logging
from typing import List, Optional

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from vayuapi import Depends, HTTPException, Request

from config.database import get_db
from models.user import User, UserRole
from utils.security import decode_token
from repositories.user import UserRepository

logger = logging.getLogger(__name__)


async def _get_token_from_request(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    # Also check cookie for SSR pages
    return request.cookies.get("access_token")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: resolve authenticated user from JWT."""
    token = await _get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_repo = UserRepository(db)
    user = await user_repo.get_with_roles(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Dependency: return user if authenticated, else None."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


def require_roles(*roles: str):
    """Dependency factory: require any of the given roles."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role_names = {ur.role.name for ur in current_user.user_roles if ur.role}
        if not any(r in user_role_names for r in roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return dependency


# Convenience shorthands
require_admin = require_roles("super_admin", "admin")
require_super_admin = require_roles("super_admin")
require_inventory = require_roles("super_admin", "admin", "inventory_manager")
require_orders = require_roles("super_admin", "admin", "order_manager")
require_support = require_roles("super_admin", "admin", "customer_support")
require_staff = require_roles("super_admin", "admin", "inventory_manager", "order_manager", "customer_support")
