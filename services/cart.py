"""Shopping cart service."""

from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.cart import Cart, CartItem
from repositories.cart import CartRepository
from repositories.product import ProductRepository, VariantRepository
from schemas.cart import CartAddSchema, CartUpdateSchema
from vayuapi import HTTPException


@dataclass
class CartData:
    id: int
    items: list
    subtotal: float
    total_items: int

    def to_dict(self) -> dict:
        return asdict(self)


class CartService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cart_repo = CartRepository(session)
        self.product_repo = ProductRepository(session)
        self.variant_repo = VariantRepository(session)

    async def get_cart(self, user_id: int) -> dict:
        cart = await self.cart_repo.get_or_create_cart(user_id)
        return await self._serialize_cart(cart)

    async def add_item(self, user_id: int, data: CartAddSchema) -> dict:
        variant = await self.variant_repo.get_by_id(data.variant_id)
        if not variant or not variant.is_in_stock:
            raise HTTPException(status_code=400, detail="Item out of stock")
        if variant.product_id != data.product_id:
            raise HTTPException(status_code=400, detail="Invalid product variant")
        if data.quantity > variant.stock_quantity:
            raise HTTPException(status_code=400, detail=f"Only {variant.stock_quantity} units available")

        cart = await self.cart_repo.get_or_create_cart(user_id)
        existing = await self.cart_repo.get_cart_item(cart.id, data.variant_id)

        if existing:
            new_qty = existing.quantity + data.quantity
            if new_qty > variant.stock_quantity:
                raise HTTPException(status_code=400, detail="Quantity exceeds available stock")
            existing.quantity = new_qty
            self.session.add(existing)
            await self.session.flush()
        else:
            self.session.add(CartItem(
                cart_id=cart.id,
                product_id=data.product_id,
                variant_id=data.variant_id,
                quantity=data.quantity,
            ))
            await self.session.flush()

        # Expire only the items collection so selectinload re-fetches it fresh
        self.session.expire(cart, ['items'])
        cart = await self.cart_repo.refresh_cart(cart)
        return await self._serialize_cart(cart)

    async def update_item(self, user_id: int, item_id: int, data: CartUpdateSchema) -> dict:
        cart = await self.cart_repo.get_cart_for_user(user_id)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        from sqlalchemy import select
        from models.cart import CartItem
        item = (await self.session.execute(
            select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        )).scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        if data.quantity == 0:
            await self.session.delete(item)
        else:
            variant = item.variant
            if not variant or not variant.is_in_stock:
                raise HTTPException(status_code=400, detail="Item out of stock")
            if data.quantity > variant.stock_quantity:
                raise HTTPException(status_code=400, detail=f"Only {variant.stock_quantity} units available")
            item.quantity = data.quantity
            self.session.add(item)
        await self.session.flush()
        self.session.expire(cart, ['items'])
        cart = await self.cart_repo.refresh_cart(cart)
        return await self._serialize_cart(cart)

    async def clear_cart(self, user_id: int) -> None:
        cart = await self.cart_repo.get_cart_for_user(user_id)
        if cart:
            for item in cart.items:
                await self.session.delete(item)
            await self.session.flush()

    async def _serialize_cart(self, cart: Cart) -> dict:
        items = []
        subtotal = Decimal("0.00")

        for item in cart.items:
            variant = item.variant
            product = item.product
            if not variant or not product:
                continue
            total = variant.price * item.quantity
            subtotal += total
            primary_image = product.primary_image if hasattr(product, "primary_image") else None
            items.append({
                "id": item.id,
                "product_id": product.id,
                "variant_id": variant.id,
                "quantity": item.quantity,
                "product_name": product.name,
                "variant_size": variant.size,
                "unit_price": float(variant.price),
                "mrp": float(variant.mrp),
                "total_price": float(total),
                "product_image": primary_image,
                "is_in_stock": variant.is_in_stock,
            })

        return CartData(
            id=cart.id,
            items=items,
            subtotal=float(subtotal),
            total_items=sum(i["quantity"] for i in items),
        )
