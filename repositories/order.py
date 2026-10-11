"""Order repository."""

from __future__ import annotations
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models.order import Order, OrderItem, OrderStatusHistory, OrderStatus
from repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Order, session)

    def _full_load(self):
        return [
            selectinload(Order.items),
            selectinload(Order.status_history),
            selectinload(Order.user),
        ]

    async def get_by_id(self, record_id: int):
        """Override base get_by_id to eagerly load all order relationships."""
        stmt = select(Order).options(*self._full_load()).where(Order.id == int(record_id))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        stmt = select(Order).options(*self._full_load()).where(Order.order_number == order_number)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_user_orders(self, user_id: int, page: int = 1, page_size: int = 10) -> Tuple[List[Order], int]:
        base = select(Order).options(*self._full_load()).where(Order.user_id == user_id)
        total = (await self.session.execute(
            select(func.count()).select_from(select(Order).where(Order.user_id == user_id).subquery())
        )).scalar_one()
        stmt = base.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.session.execute(stmt)).scalars().unique().all())
        return rows, total

    async def get_paginated_admin(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[OrderStatus] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Order], int]:
        # Build filter conditions separately so the count query stays plain SQL
        filters = []
        if status:
            filters.append(Order.status == status)
        if search:
            filters.append(Order.order_number.ilike(f"%{search}%"))

        total = (await self.session.execute(
            select(func.count(Order.id)).where(*filters)
        )).scalar_one()

        stmt = (
            select(Order)
            .options(*self._full_load())
            .where(*filters)
            .order_by(Order.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).scalars().unique().all())
        return rows, total

    async def get_revenue_stats(self) -> dict:
        from sqlalchemy import extract, and_
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_revenue = (await self.session.execute(
            select(func.sum(Order.total_amount)).where(Order.status != OrderStatus.CANCELLED)
        )).scalar_one() or 0

        today_revenue = (await self.session.execute(
            select(func.sum(Order.total_amount)).where(
                Order.created_at >= today_start,
                Order.status != OrderStatus.CANCELLED,
            )
        )).scalar_one() or 0

        month_revenue = (await self.session.execute(
            select(func.sum(Order.total_amount)).where(
                Order.created_at >= month_start,
                Order.status != OrderStatus.CANCELLED,
            )
        )).scalar_one() or 0

        total_orders = (await self.session.execute(select(func.count(Order.id)))).scalar_one()

        return {
            "total_revenue": float(total_revenue),
            "today_revenue": float(today_revenue),
            "month_revenue": float(month_revenue),
            "total_orders": total_orders,
        }
