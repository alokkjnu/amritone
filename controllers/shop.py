"""
Customer-facing shop routes — homepage, product catalog, product detail.
"""

from typing import Optional
from vayuapi import VayuAPI, Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.settings import settings
from services.product import ProductService
from middlewares.auth import get_current_user_optional
from models.banner import Banner
from models.user import User

router = VayuAPI()
from config.templates import templates


@router.get("/")
async def homepage(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    svc = ProductService(db)
    data = await svc.get_homepage_data()
    hero_banners = list((await db.execute(
        select(Banner)
        .where(Banner.position == "hero", Banner.is_active == True)
        .order_by(Banner.sort_order)
    )).scalars().all())
    return templates.TemplateResponse("shop/home.html", {
        "request": request,
        "current_user": current_user,
        "settings": settings,
        "hero_banners": hero_banners,
        **data,
    })


@router.get("/shop")
async def shop_page(
    request: Request,
    page: int = 1,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: str = "created_at",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    svc = ProductService(db)
    category_obj = None
    category_id = None
    if category:
        from repositories.product import CategoryRepository
        cat_repo = CategoryRepository(db)
        category_obj = await cat_repo.get_by_slug(category)
        if category_obj:
            category_id = category_obj.id

    result = await svc.list_products(
        page=page,
        page_size=12,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort,
        sort_order=order,
    )
    categories = await svc.get_categories()
    return templates.TemplateResponse("shop/catalog.html", {
        "request": request,
        "current_user": current_user,
        "settings": settings,
        "products": result.items,
        "total": result.total,
        "page": result.page,
        "total_pages": result.total_pages,
        "categories": categories,
        "active_category": category_obj,
        "search": search,
        "sort": sort,
        "order": order,
    })


@router.get("/product/{slug}")
async def product_detail(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    svc = ProductService(db)
    product = await svc.get_product_by_slug(slug)
    related = await svc.product_repo.get_related(product.id, product.category_id)
    return templates.TemplateResponse("shop/product_detail.html", {
        "request": request,
        "current_user": current_user,
        "settings": settings,
        "product": product,
        "related_products": related,
    })


@router.get("/category/{slug}")
async def category_page(
    request: Request,
    slug: str,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    from repositories.product import CategoryRepository
    cat_repo = CategoryRepository(db)
    category = await cat_repo.get_by_slug(slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    svc = ProductService(db)
    result = await svc.list_products(page=page, page_size=12, category_id=category.id)
    return templates.TemplateResponse("shop/catalog.html", {
        "request": request,
        "current_user": current_user,
        "settings": settings,
        "products": result.items,
        "total": result.total,
        "page": result.page,
        "total_pages": result.total_pages,
        "active_category": category,
        "categories": await svc.get_categories(),
    })


@router.get("/search")
async def search_page(
    request: Request,
    q: str = "",
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    svc = ProductService(db)
    result = await svc.list_products(page=page, page_size=12, search=q)
    return templates.TemplateResponse("shop/catalog.html", {
        "request": request,
        "current_user": current_user,
        "settings": settings,
        "products": result.items,
        "total": result.total,
        "page": result.page,
        "total_pages": result.total_pages,
        "categories": await svc.get_categories(),
        "search": q,
    })


@router.get("/privacy")
async def privacy_policy(request: Request):
    return templates.TemplateResponse("shop/privacy.html", {
        "request": request, "settings": settings,
    })


@router.get("/terms")
async def terms_conditions(request: Request):
    return templates.TemplateResponse("shop/terms.html", {
        "request": request, "settings": settings,
    })


@router.get("/shipping")
async def shipping_policy(request: Request):
    return templates.TemplateResponse("shop/shipping.html", {
        "request": request, "settings": settings,
    })


@router.get("/returns")
async def returns_policy(request: Request):
    return templates.TemplateResponse("shop/returns.html", {
        "request": request, "settings": settings,
    })
