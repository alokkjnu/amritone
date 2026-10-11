"""Cart and checkout route handlers."""

from typing import Optional
from vayuapi import VayuAPI, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.settings import settings
from middlewares.auth import get_current_user
from models.user import User
from services.cart import CartService
from services.order import OrderService
from schemas.cart import CartAddSchema, CartUpdateSchema, CouponApplySchema
from schemas.order import CheckoutSchema

router = VayuAPI()
from config.templates import templates


@router.get("/cart")
async def cart_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    cart = await svc.get_cart(current_user.id)
    return templates.TemplateResponse("shop/cart.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "cart": cart,
    })


@router.get("/api/cart")
async def get_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    return (await svc.get_cart(current_user.id)).to_dict()


@router.post("/api/cart/add")
async def add_to_cart(
    data: CartAddSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    cart = await svc.add_item(current_user.id, data)
    return {"message": "Added to cart", "cart": cart.to_dict()}


@router.put("/api/cart/items/{item_id}")
async def update_cart_item(
    item_id: int,
    data: CartUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    return (await svc.update_item(current_user.id, item_id, data)).to_dict()


@router.delete("/api/cart/items/{item_id}")
async def remove_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    data = CartUpdateSchema(quantity=0)
    return (await svc.update_item(current_user.id, item_id, data)).to_dict()


@router.post("/api/cart/coupon")
async def apply_coupon(
    data: CouponApplySchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from repositories.coupon import CouponRepository
    from datetime import datetime, timezone
    repo = CouponRepository(db)
    coupon = await repo.get_by_code(data.code)
    if not coupon or not coupon.is_active:
        raise HTTPException(status_code=400, detail="Invalid or inactive coupon")
    now = datetime.now(timezone.utc)
    if coupon.valid_until and now > coupon.valid_until:
        raise HTTPException(status_code=400, detail="Coupon has expired")
    return {
        "valid": True,
        "code": coupon.code,
        "type": coupon.coupon_type.value,
        "discount_value": float(coupon.discount_value),
        "description": coupon.description,
    }


@router.get("/checkout")
async def checkout_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CartService(db)
    cart = await svc.get_cart(current_user.id)
    if not cart.items:
        from vayuapi.response import RedirectResponse
        return RedirectResponse("/cart", status_code=302)

    from repositories.user import UserRepository
    user_repo = UserRepository(db)
    addresses = await user_repo.get_addresses(current_user.id)
    return templates.TemplateResponse("shop/checkout.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "cart": cart, "addresses": addresses,
    })


@router.post("/api/checkout")
async def process_checkout(
    data: CheckoutSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrderService(db)
    order = await svc.checkout(current_user.id, data)
    return {
        "message": "Order placed successfully",
        "order_number": order.order_number,
        "redirect": f"/account/orders/{order.order_number}",
    }
