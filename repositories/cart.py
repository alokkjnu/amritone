"""Cart repository."""

from __future__ import annotations
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models.cart import Cart, CartItem
from models.product import Product, ProductVariant
from repositories.base import BaseRepository


class CartRepository(BaseRepository[Cart]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Cart, session)

    def _eager_options(self):
        return [
            selectinload(Cart.items).options(
                selectinload(CartItem.product).selectinload(Product.images),
                selectinload(CartItem.variant),
            ),
        ]

    async def get_cart_for_user(self, user_id: int) -> Optional[Cart]:
        stmt = (
            select(Cart)
            .options(*self._eager_options())
            .where(Cart.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_or_create_cart(self, user_id: int) -> Cart:
        cart = await self.get_cart_for_user(user_id)
        if not cart:
            cart = await self.create(user_id=user_id)
            cart = await self.refresh_cart(cart)
        return cart

    async def refresh_cart(self, cart: Cart) -> Cart:
        """Re-fetch cart with all relationships eagerly loaded, bypassing identity map cache."""
        stmt = (
            select(Cart)
            .options(*self._eager_options())
            .where(Cart.id == cart.id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_cart_item(self, cart_id: int, variant_id: int) -> Optional[CartItem]:
        stmt = select(CartItem).where(CartItem.cart_id == cart_id, CartItem.variant_id == variant_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()
