"""Customer portal routes — profile, addresses, orders, wishlist."""

from typing import Optional
from vayuapi import VayuAPI, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.settings import settings
from middlewares.auth import get_current_user
from models.user import User
from repositories.user import UserRepository
from repositories.order import OrderRepository
from repositories.product import ProductRepository
from schemas.user import UserProfileUpdateSchema, AddressCreateSchema
from services.pdf import InvoicePDFService
from vayuapi.response import Response

router = VayuAPI()
from config.templates import templates


@router.get("/account")
async def account_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_repo = OrderRepository(db)
    orders, _ = await order_repo.get_user_orders(current_user.id, page=1, page_size=5)
    return templates.TemplateResponse("shop/account/dashboard.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "recent_orders": orders,
    })


@router.get("/account/profile")
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse("shop/account/profile.html", {
        "request": request, "current_user": current_user, "settings": settings,
    })


@router.put("/api/account/profile")
async def update_profile(
    data: UserProfileUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = UserRepository(db)
    updated = await repo.update(current_user, **data.model_dump(exclude_none=True))
    return {"message": "Profile updated", "user": {"first_name": updated.first_name, "last_name": updated.last_name}}


@router.get("/account/addresses")
async def addresses_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = UserRepository(db)
    addresses = await repo.get_addresses(current_user.id)
    return templates.TemplateResponse("shop/account/addresses.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "addresses": addresses,
    })


@router.post("/api/account/addresses")
async def add_address(
    data: AddressCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from models.user import UserAddress
    repo = UserRepository(db)
    if data.is_default:
        await repo.clear_default_address(current_user.id)
    address = UserAddress(user_id=current_user.id, **data.model_dump())
    db.add(address)
    await db.flush()
    return {"message": "Address added", "address_id": address.id}


@router.delete("/api/account/addresses/{address_id}")
async def delete_address(
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = UserRepository(db)
    address = await repo.get_address_by_id(address_id, current_user.id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    await db.delete(address)
    await db.flush()
    return {"message": "Address deleted"}


@router.get("/account/orders")
async def orders_page(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = OrderRepository(db)
    orders, total = await repo.get_user_orders(current_user.id, page=page, page_size=10)
    return templates.TemplateResponse("shop/account/orders.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "orders": orders,
        "total": total, "page": page,
    })


@router.get("/account/orders/{order_number}")
async def order_detail_page(
    request: Request,
    order_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = OrderRepository(db)
    order = await repo.get_by_order_number(order_number)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse("shop/account/order_detail.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "order": order,
    })


@router.get("/account/orders/{order_number}/invoice")
async def download_invoice(
    order_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = OrderRepository(db)
    order = await repo.get_by_order_number(order_number)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    pdf_svc = InvoicePDFService()
    pdf_bytes = pdf_svc.generate_invoice(order)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice-{order_number}.pdf"},
    )


@router.get("/wishlist")
async def wishlist_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from models.wishlist import Wishlist, WishlistItem
    from sqlalchemy.orm import selectinload
    from models.product import Product, ProductVariant, ProductImage
    stmt = (
        select(Wishlist)
        .options(
            selectinload(Wishlist.items).selectinload(WishlistItem.product).selectinload(Product.variants),
            selectinload(Wishlist.items).selectinload(WishlistItem.product).selectinload(Product.category),
            selectinload(Wishlist.items).selectinload(WishlistItem.product).selectinload(Product.images),
        )
        .where(Wishlist.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    wishlist = result.scalar_one_or_none()
    return templates.TemplateResponse("shop/account/wishlist.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "wishlist": wishlist,
    })


@router.post("/api/wishlist/toggle/{product_id}")
async def toggle_wishlist(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select
    from models.wishlist import Wishlist, WishlistItem
    # Get or create wishlist
    stmt = select(Wishlist).where(Wishlist.user_id == current_user.id)
    wishlist = (await db.execute(stmt)).scalar_one_or_none()
    if not wishlist:
        wishlist = Wishlist(user_id=current_user.id)
        db.add(wishlist)
        await db.flush()

    # Toggle item
    stmt2 = select(WishlistItem).where(
        WishlistItem.wishlist_id == wishlist.id,
        WishlistItem.product_id == product_id,
    )
    existing = (await db.execute(stmt2)).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        action = "removed"
    else:
        db.add(WishlistItem(wishlist_id=wishlist.id, product_id=product_id))
        action = "added"
    await db.flush()
    return {"action": action, "product_id": product_id}
