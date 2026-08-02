"""Coupon repository."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.coupon import Coupon, CouponUsage
from repositories.base import BaseRepository


class CouponRepository(BaseRepository[Coupon]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Coupon, session)

    async def get_by_code(self, code: str) -> Optional[Coupon]:
        stmt = select(Coupon).where(Coupon.code == code.upper())
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_user_usage_count(self, coupon_id: int, user_id: int) -> int:
        from sqlalchemy import func
        stmt = select(func.count(CouponUsage.id)).where(
            CouponUsage.coupon_id == coupon_id,
            CouponUsage.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one()
