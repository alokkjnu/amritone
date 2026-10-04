"""
Admin portal controllers — dashboard, products, orders, customers,
inventory, coupons, blogs, banners, reviews, reports, settings.
"""

import json
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from vayuapi import Depends, HTTPException, VayuAPI, Request
from vayuapi import Jinja2Templates

from config.database import get_db
from config.settings import settings
from middlewares.auth import require_admin, require_inventory, require_orders, require_super_admin
from models.blog import Blog, BlogCategory, BlogStatus
from models.banner import Banner
from models.coupon import Coupon, CouponType
from models.inventory import InventoryAction, InventoryLog
from models.newsletter import NewsletterSubscriber
from models.order import Order, OrderStatus, PaymentStatus
from models.product import Brand, Category, Product, ProductStatus, ProductVariant, Tag, VariantStatus
from models.review import Review
from models.return_request import ReturnRequest, ReturnStatus
from models.user import User
from repositories.order import OrderRepository
from repositories.product import CategoryRepository, ProductRepository, VariantRepository
from repositories.user import UserRepository
from schemas.order import OrderStatusUpdateSchema, PaymentStatusUpdateSchema
from schemas.product import ProductCreateSchema
from services.order import OrderService
from services.pdf import InvoicePDFService
from services.product import ProductService
from utils.slugify import make_slug

router = VayuAPI()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/admin")
@router.get("/admin/dashboard")
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    order_repo = OrderRepository(db)
    stats = await order_repo.get_revenue_stats()

    total_products = (await db.execute(select(func.count(Product.id)))).scalar_one()
    total_customers = (await db.execute(
        select(func.count(User.id)).where(User.is_staff == False)
    )).scalar_one()
    low_stock_count = (await db.execute(
        select(func.count(ProductVariant.id)).where(
            ProductVariant.stock_quantity <= ProductVariant.low_stock_alert
        )
    )).scalar_one()

    recent_orders = list((await db.execute(
        select(Order).order_by(Order.created_at.desc()).limit(10)
    )).scalars().all())

    pending_reviews = (await db.execute(
        select(func.count(Review.id)).where(Review.is_approved == False)
    )).scalar_one()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "stats": stats, "total_products": total_products,
        "total_customers": total_customers, "low_stock_count": low_stock_count,
        "recent_orders": recent_orders, "pending_reviews": pending_reviews,
    })


# ── Products ──────────────────────────────────────────────────────────────────

@router.get("/admin/products")
async def admin_products_list(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    product_repo = ProductRepository(db)
    status_filter = ProductStatus(status) if status else ProductStatus.PUBLISHED
    items, total = await product_repo.get_paginated(
        page=page, page_size=20, search=search, status=status_filter
    )
    categories = await CategoryRepository(db).get_active()
    return templates.TemplateResponse("admin/products/list.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "products": items, "total": total, "page": page,
        "total_pages": (total + 19) // 20, "search": search,
        "categories": categories, "status_filter": status,
    })


@router.get("/admin/products/new")
async def admin_product_new_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    categories = list((await db.execute(select(Category))).scalars().all())
    brands = list((await db.execute(select(Brand))).scalars().all())
    tags = list((await db.execute(select(Tag))).scalars().all())
    return templates.TemplateResponse("admin/products/form.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "product": None, "categories": categories, "brands": brands, "tags": tags,
    })


@router.post("/api/admin/products")
async def admin_create_product(
    data: ProductCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    svc = ProductService(db)
    product = await svc.create_product(data)
    return {"message": "Product created", "product_id": product.id, "slug": product.slug}


@router.get("/admin/products/{product_id}/edit")
async def admin_product_edit_form(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    product_repo = ProductRepository(db)
    product = await product_repo.get_with_relations(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    categories = list((await db.execute(select(Category))).scalars().all())
    brands = list((await db.execute(select(Brand))).scalars().all())
    tags = list((await db.execute(select(Tag))).scalars().all())
    return templates.TemplateResponse("admin/products/form.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "product": product, "categories": categories, "brands": brands, "tags": tags,
    })


@router.put("/api/admin/products/{product_id}")
async def admin_update_product(
    product_id: int,
    data: ProductCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    product_repo = ProductRepository(db)
    product = await product_repo.get_with_relations(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    update_data = data.model_dump(exclude_none=True, exclude={"tag_ids"})
    await product_repo.update(product, **update_data)
    if data.tag_ids is not None:
        tags = list((await db.execute(select(Tag).where(Tag.id.in_(data.tag_ids)))).scalars().all())
        product.tags = tags
        await db.flush()
    return {"message": "Product updated"}


@router.delete("/api/admin/products/{product_id}")
async def admin_delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    product_repo = ProductRepository(db)
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await product_repo.delete(product)
    return {"message": "Product deleted"}


# ── Variants ──────────────────────────────────────────────────────────────────

@router.post("/api/admin/products/{product_id}/variants")
async def admin_add_variant(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    body = await request.json()
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    variant = ProductVariant(
        product_id=product_id,
        size=body["size"],
        sku=body["sku"],
        barcode=body.get("barcode"),
        price=body["price"],
        mrp=body["mrp"],
        discount_percent=body.get("discount_percent", 0),
        gst_percent=body.get("gst_percent", 5),
        stock_quantity=body.get("stock_quantity", 0),
        low_stock_alert=body.get("low_stock_alert", 10),
        weight_grams=body["weight_grams"],
    )
    db.add(variant)
    await db.flush()
    return {"message": "Variant added", "variant_id": variant.id}


@router.put("/api/admin/variants/{variant_id}")
async def admin_update_variant(
    variant_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    variant = await db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    body = await request.json()
    for k, v in body.items():
        if hasattr(variant, k):
            setattr(variant, k, v)
    db.add(variant)
    await db.flush()
    return {"message": "Variant updated"}


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/admin/categories")
async def admin_categories_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    categories = list((await db.execute(select(Category).order_by(Category.sort_order))).scalars().all())
    return templates.TemplateResponse("admin/categories/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "categories": categories,
    })


@router.post("/api/admin/categories")
async def admin_create_category(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    body = await request.json()
    name = body.get("name", "")
    slug = body.get("slug") or make_slug(name)
    cat = Category(
        name=name, slug=slug,
        description=body.get("description"),
        parent_id=body.get("parent_id"),
        meta_title=body.get("meta_title"),
        meta_description=body.get("meta_description"),
    )
    db.add(cat)
    await db.flush()
    return {"message": "Category created", "id": cat.id}


@router.put("/api/admin/categories/{cat_id}")
async def admin_update_category(
    cat_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    cat = await db.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    body = await request.json()
    for k, v in body.items():
        if hasattr(cat, k):
            setattr(cat, k, v)
    db.add(cat)
    await db.flush()
    return {"message": "Category updated"}


# ── Inventory ─────────────────────────────────────────────────────────────────

@router.get("/admin/inventory")
async def admin_inventory(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_inventory),
):
    from sqlalchemy.orm import selectinload
    page_size = 30
    total = (await db.execute(select(func.count(ProductVariant.id)))).scalar_one()
    variants = list((await db.execute(
        select(ProductVariant)
        .options(selectinload(ProductVariant.product))
        .order_by(ProductVariant.stock_quantity.asc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return templates.TemplateResponse("admin/inventory/list.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "variants": variants, "total": total, "page": page,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.post("/api/admin/inventory/stock-in")
async def admin_stock_in(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_inventory),
):
    body = await request.json()
    variant_id = int(body["variant_id"])
    quantity = int(body["quantity"])
    notes = body.get("notes", "")
    variant = await db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    qty_before = variant.stock_quantity
    variant.stock_quantity += quantity
    db.add(variant)
    db.add(InventoryLog(
        variant_id=variant_id,
        action=InventoryAction.STOCK_IN,
        quantity_change=quantity,
        quantity_before=qty_before,
        quantity_after=variant.stock_quantity,
        notes=notes,
        performed_by=current_user.id,
    ))
    await db.flush()
    return {"message": f"Stock updated. New quantity: {variant.stock_quantity}"}


def _inventory_variant_payload(variant: ProductVariant) -> dict:
    return {
        "id": variant.id,
        "product_id": variant.product_id,
        "product_name": variant.product.name if variant.product else "N/A",
        "size": variant.size,
        "sku": variant.sku,
        "price": float(variant.price),
        "mrp": float(variant.mrp),
        "stock_quantity": variant.stock_quantity,
        "low_stock_alert": variant.low_stock_alert,
        "status": variant.status.value,
        "is_in_stock": variant.is_in_stock,
        "is_low_stock": variant.is_low_stock,
    }


@router.get("/api/admin/inventory/variants/{variant_id}")
async def admin_inventory_variant_detail(
    variant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_inventory),
):
    from sqlalchemy.orm import selectinload

    variant = (await db.execute(
        select(ProductVariant)
        .options(selectinload(ProductVariant.product))
        .where(ProductVariant.id == variant_id)
    )).scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return _inventory_variant_payload(variant)


@router.put("/api/admin/inventory/variants/{variant_id}")
async def admin_inventory_update_variant(
    variant_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_inventory),
):
    variant = await db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    body = await request.json()
    if "stock_quantity" in body:
        stock_quantity = int(body["stock_quantity"])
        if stock_quantity < 0:
            raise HTTPException(status_code=400, detail="Stock quantity must be 0 or more")
        variant.stock_quantity = stock_quantity

    if "low_stock_alert" in body:
        low_stock_alert = int(body["low_stock_alert"])
        if low_stock_alert < 0:
            raise HTTPException(status_code=400, detail="Low stock alert must be 0 or more")
        variant.low_stock_alert = low_stock_alert

    if "status" in body and body.get("status"):
        try:
            variant.status = VariantStatus(str(body["status"]).strip().lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid variant status")

    if variant.stock_quantity <= 0:
        variant.status = VariantStatus.OUT_OF_STOCK
    elif variant.status == VariantStatus.OUT_OF_STOCK:
        variant.status = VariantStatus.ACTIVE

    db.add(variant)
    await db.flush()
    return {
        "message": "Variant inventory updated",
        "variant": {
            "id": variant.id,
            "stock_quantity": variant.stock_quantity,
            "low_stock_alert": variant.low_stock_alert,
            "status": variant.status.value,
            "is_in_stock": variant.is_in_stock,
        },
    }


@router.post("/api/admin/inventory/stock-out")
async def admin_stock_out(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_inventory),
):
    body = await request.json()
    variant_id = int(body["variant_id"])
    notes = body.get("notes", "")

    variant = await db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    qty_before = variant.stock_quantity
    variant.stock_quantity = 0
    variant.status = VariantStatus.OUT_OF_STOCK
    db.add(variant)
    db.add(InventoryLog(
        variant_id=variant_id,
        action=InventoryAction.STOCK_OUT,
        quantity_change=(-qty_before if qty_before > 0 else 0),
        quantity_before=qty_before,
        quantity_after=0,
        notes=notes,
        performed_by=current_user.id,
    ))
    await db.flush()

    if qty_before > 0:
        message = "Variant stocked out successfully"
    else:
        message = "Variant is already out of stock"
    return {"message": message}


@router.delete("/api/admin/inventory/variants/{variant_id}")
async def admin_inventory_delete_variant(
    variant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_inventory),
):
    variant = await db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    await db.delete(variant)
    await db.flush()
    return {"message": "Variant deleted"}


@router.get("/api/admin/inventory/low-stock")
async def admin_low_stock(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_inventory),
):
    from sqlalchemy.orm import selectinload
    variants = list((await db.execute(
        select(ProductVariant)
        .options(selectinload(ProductVariant.product))
        .where(ProductVariant.stock_quantity <= ProductVariant.low_stock_alert)
    )).scalars().all())
    return [
        {
            "variant_id": v.id, "sku": v.sku,
            "product_name": v.product.name if v.product else "N/A",
            "size": v.size, "stock": v.stock_quantity, "threshold": v.low_stock_alert,
        }
        for v in variants
    ]


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/admin/orders")
async def admin_orders_list(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_orders),
):
    order_repo = OrderRepository(db)
    status_filter = OrderStatus(status) if status else None
    orders, total = await order_repo.get_paginated_admin(
        page=page, page_size=20, status=status_filter, search=search
    )
    return templates.TemplateResponse("admin/orders/list.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "orders": orders, "total": total, "page": page,
        "total_pages": (total + 19) // 20,
        "status_filter": status, "search": search,
        "statuses": [s.value for s in OrderStatus],
    })


@router.get("/admin/orders/{order_id}")
async def admin_order_detail(
    request: Request,
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_orders),
):
    order_repo = OrderRepository(db)
    order = await order_repo.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse("admin/orders/detail.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "order": order,
        "statuses": [s.value for s in OrderStatus],
        "payment_statuses": [s.value for s in PaymentStatus],
    })


@router.put("/api/admin/orders/{order_id}/status")
async def admin_update_order_status(
    order_id: int,
    data: OrderStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_orders),
):
    svc = OrderService(db)
    await svc.update_status(order_id, data, current_user.id)
    return {"message": "Order status updated"}


@router.put("/api/admin/orders/{order_id}/payment-status")
async def admin_update_payment_status(
    order_id: int,
    data: PaymentStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_orders),
):
    from sqlalchemy import select as sa_select
    stmt = sa_select(Order).where(Order.id == int(order_id))
    order = (await db.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.payment_status = data.payment_status
    if data.payment_reference is not None:
        order.payment_reference = data.payment_reference
    await db.flush()
    return {"message": "Payment status updated"}


@router.get("/api/admin/orders/{order_id}/invoice")
async def admin_download_invoice(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_orders),
):
    from vayuapi.response import Response
    order_repo = OrderRepository(db)
    order = await order_repo.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    pdf_svc = InvoicePDFService()
    pdf_bytes = pdf_svc.generate_invoice(order)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice-{order.order_number}.pdf"},
    )


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/admin/customers")
async def admin_customers_list(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user_repo = UserRepository(db)
    users, total = await user_repo.get_paginated(page=page, page_size=20, search=search or "")
    return templates.TemplateResponse("admin/customers/list.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "users": users, "total": total, "page": page,
        "total_pages": (total + 19) // 20, "search": search,
    })


@router.put("/api/admin/customers/{user_id}/toggle-active")
async def admin_toggle_customer(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user_repo.update(user, is_active=not user.is_active)
    return {"message": f"User {'activated' if user.is_active else 'deactivated'}"}


# ── Coupons ───────────────────────────────────────────────────────────────────

@router.get("/admin/coupons")
async def admin_coupons_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    coupons = list((await db.execute(
        select(Coupon).order_by(Coupon.created_at.desc())
    )).scalars().all())
    return templates.TemplateResponse("admin/coupons/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "coupons": coupons,
    })


@router.post("/api/admin/coupons")
async def admin_create_coupon(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from datetime import datetime
    body = await request.json()
    coupon = Coupon(
        code=body["code"].upper(),
        description=body.get("description"),
        coupon_type=CouponType(body["coupon_type"]),
        discount_value=body["discount_value"],
        max_discount=body.get("max_discount"),
        min_order_amount=body.get("min_order_amount", 0),
        usage_limit=body.get("usage_limit"),
        per_user_limit=body.get("per_user_limit", 1),
        is_active=body.get("is_active", True),
        valid_from=datetime.fromisoformat(body["valid_from"]),
        valid_until=datetime.fromisoformat(body["valid_until"]) if body.get("valid_until") else None,
        applicable_category_id=body.get("applicable_category_id"),
        applicable_product_id=body.get("applicable_product_id"),
    )
    db.add(coupon)
    await db.flush()
    return {"message": "Coupon created", "id": coupon.id}


@router.delete("/api/admin/coupons/{coupon_id}")
async def admin_delete_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    coupon = await db.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    await db.delete(coupon)
    await db.flush()
    return {"message": "Coupon deleted"}


# ── Banners ───────────────────────────────────────────────────────────────────

@router.get("/admin/banners")
async def admin_banners_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    banners = list((await db.execute(
        select(Banner).order_by(Banner.sort_order)
    )).scalars().all())
    return templates.TemplateResponse("admin/banners/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "banners": banners,
    })


@router.post("/api/admin/banners")
async def admin_create_banner(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    body = await request.json()
    banner = Banner(**{k: v for k, v in body.items() if hasattr(Banner, k)})
    db.add(banner)
    await db.flush()
    return {"message": "Banner created", "id": banner.id}


@router.delete("/api/admin/banners/{banner_id}")
async def admin_delete_banner(
    banner_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    banner = await db.get(Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    await db.delete(banner)
    await db.flush()
    return {"message": "Banner deleted"}


# ── Blogs ─────────────────────────────────────────────────────────────────────

@router.get("/admin/blogs")
async def admin_blogs_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    blogs = list((await db.execute(
        select(Blog).order_by(Blog.created_at.desc())
    )).scalars().all())
    return templates.TemplateResponse("admin/blogs/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "blogs": blogs,
    })


@router.get("/admin/blogs/new")
async def admin_blog_new_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    categories = list((await db.execute(select(BlogCategory))).scalars().all())
    return templates.TemplateResponse("admin/blogs/form.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "blog": None, "categories": categories,
    })


@router.post("/api/admin/blogs")
async def admin_create_blog(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    body = await request.json()
    slug = body.get("slug") or make_slug(body["title"])
    blog = Blog(
        title=body["title"], slug=slug,
        excerpt=body.get("excerpt"), content=body.get("content"),
        featured_image=body.get("featured_image"),
        category_id=body.get("category_id"),
        author_id=current_user.id,
        status=BlogStatus(body.get("status", "draft")),
        is_featured=body.get("is_featured", False),
        meta_title=body.get("meta_title"),
        meta_description=body.get("meta_description"),
        meta_keywords=body.get("meta_keywords"),
    )
    db.add(blog)
    await db.flush()
    return {"message": "Blog created", "id": blog.id}


@router.put("/api/admin/blogs/{blog_id}")
async def admin_update_blog(
    blog_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    blog = await db.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    body = await request.json()
    for k, v in body.items():
        if hasattr(blog, k):
            setattr(blog, k, v)
    db.add(blog)
    await db.flush()
    return {"message": "Blog updated"}


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.get("/admin/reviews")
async def admin_reviews_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from sqlalchemy.orm import selectinload
    reviews = list((await db.execute(
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.product))
        .order_by(Review.created_at.desc())
    )).scalars().all())
    return templates.TemplateResponse("admin/reviews/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "reviews": reviews,
    })


@router.put("/api/admin/reviews/{review_id}/approve")
async def admin_approve_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.is_approved = True
    db.add(review)
    await db.flush()
    # Update product rating
    from services.product import ProductService
    svc = ProductService(db)
    await svc.update_product_rating(review.product_id)
    return {"message": "Review approved"}


@router.delete("/api/admin/reviews/{review_id}")
async def admin_delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.delete(review)
    await db.flush()
    return {"message": "Review deleted"}


# ── Newsletter ────────────────────────────────────────────────────────────────

@router.get("/admin/newsletter")
async def admin_newsletter(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    subscribers = list((await db.execute(
        select(NewsletterSubscriber).order_by(NewsletterSubscriber.created_at.desc())
    )).scalars().all())
    return templates.TemplateResponse("admin/newsletter/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "subscribers": subscribers,
    })


# ── Returns ───────────────────────────────────────────────────────────────────

@router.get("/admin/returns")
async def admin_returns_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_orders),
):
    from sqlalchemy.orm import selectinload
    returns = list((await db.execute(
        select(ReturnRequest)
        .options(selectinload(ReturnRequest.order))
        .order_by(ReturnRequest.created_at.desc())
    )).scalars().all())
    return templates.TemplateResponse("admin/returns/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "returns": returns,
    })


@router.put("/api/admin/returns/{return_id}/status")
async def admin_update_return_status(
    return_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_orders),
):
    body = await request.json()
    ret = await db.get(ReturnRequest, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    ret.status = ReturnStatus(body["status"])
    ret.admin_notes = body.get("admin_notes", ret.admin_notes)
    db.add(ret)
    await db.flush()
    return {"message": "Return status updated"}


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/admin/reports")
async def admin_reports(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    order_repo = OrderRepository(db)
    stats = await order_repo.get_revenue_stats()

    # Sales by status
    status_counts = {}
    for status in OrderStatus:
        cnt = (await db.execute(
            select(func.count(Order.id)).where(Order.status == status)
        )).scalar_one()
        status_counts[status.value] = cnt

    # Top products by revenue
    from sqlalchemy import desc
    from models.order import OrderItem
    top_products = list((await db.execute(
        select(
            OrderItem.product_name,
            func.sum(OrderItem.total_price).label("revenue"),
            func.sum(OrderItem.quantity).label("units"),
        )
        .group_by(OrderItem.product_name)
        .order_by(desc("revenue"))
        .limit(10)
    )).all())

    return templates.TemplateResponse("admin/reports/dashboard.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "stats": stats, "status_counts": status_counts, "top_products": top_products,
    })


# ── Media Manager ─────────────────────────────────────────────────────────────

@router.get("/admin/media")
async def admin_media_list(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.media import Media
    page_size = 30
    total = (await db.execute(select(func.count(Media.id)))).scalar_one()
    media = list((await db.execute(
        select(Media).order_by(Media.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return templates.TemplateResponse("admin/media/list.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "media": media, "total": total, "page": page,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.post("/api/admin/media/upload")
async def admin_upload_media(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.media import Media
    from utils.image import VIDEO_MIME_TYPES, VIDEO_EXTENSIONS, save_uploaded_file
    from pathlib import Path as _Path
    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    file_data = await file.read()
    mime = file.content_type or ""
    ext = _Path(file.filename or "").suffix.lower()
    is_video = mime in VIDEO_MIME_TYPES or ext in VIDEO_EXTENSIONS
    max_mb = settings.MAX_UPLOAD_SIZE_MB * (20 if is_video else 1)
    if len(file_data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    url = await save_uploaded_file(file_data, filename=file.filename or "file", mime_type=mime, subfolder="media")
    media = Media(
        file_name=file.filename,
        file_path=url,
        file_type="video" if is_video else "image",
        file_size=len(file_data),
        mime_type=mime or ("video/mp4" if is_video else "image/webp"),
        uploaded_by=current_user.id,
    )
    db.add(media)
    await db.flush()
    return {"url": url, "media_id": media.id, "file_type": media.file_type}


@router.delete("/api/admin/media/{media_id}")
async def admin_delete_media(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    import os
    from models.media import Media
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    # Remove file from disk if it lives under UPLOAD_DIR
    try:
        rel = media.file_path.lstrip("/static/")
        disk_path = settings.UPLOAD_DIR.parent / rel
        if disk_path.exists():
            os.remove(disk_path)
    except Exception:
        pass
    await db.delete(media)
    await db.flush()
    return {"message": "Deleted"}


# ── Product Images ────────────────────────────────────────────────────────────

@router.post("/api/admin/products/{product_id}/images")
async def admin_add_product_image(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.product import ProductImage
    exists = (await db.execute(
        select(func.count(Product.id)).where(Product.id == product_id)
    )).scalar_one()
    if not exists:
        raise HTTPException(status_code=404, detail="Product not found")
    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    existing_count = (await db.execute(
        select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)
    )).scalar_one()
    img = ProductImage(
        product_id=product_id,
        image_url=url,
        alt_text=body.get("alt_text") or None,
        is_primary=body.get("is_primary", existing_count == 0),
        sort_order=body.get("sort_order", existing_count),
    )
    db.add(img)
    await db.flush()
    return {"message": "Image added", "id": img.id, "url": img.image_url, "is_primary": img.is_primary}


@router.delete("/api/admin/products/{product_id}/images/{image_id}")
async def admin_delete_product_image(
    product_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.product import ProductImage
    img = await db.get(ProductImage, image_id)
    if not img or img.product_id != product_id:
        raise HTTPException(status_code=404, detail="Image not found")
    await db.delete(img)
    await db.flush()
    return {"message": "Image removed"}


@router.put("/api/admin/products/{product_id}/images/{image_id}/primary")
async def admin_set_primary_product_image(
    product_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.product import ProductImage
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(ProductImage)
        .where(ProductImage.product_id == product_id)
        .values(is_primary=False)
    )
    img = await db.get(ProductImage, image_id)
    if not img or img.product_id != product_id:
        raise HTTPException(status_code=404, detail="Image not found")
    img.is_primary = True
    db.add(img)
    await db.flush()
    return {"message": "Primary image set"}


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/admin/audit-logs")
async def admin_audit_logs(
    request: Request,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    from models.audit import AuditLog
    page_size = 50
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar_one()
    logs = list((await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return templates.TemplateResponse("admin/audit/list.html", {
        "request": request, "current_user": current_user, "settings": settings,
        "logs": logs, "total": total, "page": page,
        "total_pages": (total + page_size - 1) // page_size,
    })


# ── Site Settings ─────────────────────────────────────────────────────────────

@router.get("/admin/settings")
async def admin_settings_page(
    request: Request,
    current_user: User = Depends(require_super_admin),
):
    return templates.TemplateResponse("admin/settings/general.html", {
        "request": request, "current_user": current_user, "settings": settings,
    })
