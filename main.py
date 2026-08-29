"""
Amrit One — Main Application Entry Point
Pure. Natural. Authentic.

Uses VayuAPI (https://vayuapi.amrits.in) as the async web framework.
"""

from __future__ import annotations

import logging
from pathlib import Path

from vayuapi import VayuAPI
from vayuapi import StaticFiles

from config.settings import settings
from config.database import create_all_tables, DatabaseSessionMiddleware
from config.templates import templates  # shared instance with registered filters
from middlewares.security import SecurityHeadersMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.audit import AuditMiddleware
from utils.logging import setup_logging

# Controllers
from controllers.shop import router as shop_router
from controllers.auth import router as auth_router
from controllers.customer import router as customer_router
from controllers.cart_checkout import router as cart_router
from controllers.admin import router as admin_router
from controllers.blog import router as blog_router
from controllers.api import router as api_router
from controllers.seo import router as seo_router

setup_logging()
logger = logging.getLogger(__name__)

# ── Application factory ────────────────────────────────────────────────────────

def create_app() -> VayuAPI:
    """Build and configure the VayuAPI application."""

    app = VayuAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # ── Static files ──────────────────────────────────────────────────────────
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # ── Middleware stack ──────────────────────────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(DatabaseSessionMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(seo_router)
    app.include_router(auth_router)
    app.include_router(shop_router)
    app.include_router(customer_router)
    app.include_router(cart_router)
    app.include_router(admin_router)
    app.include_router(blog_router)
    app.include_router(api_router)

    # ── Additional page routes ─────────────────────────────────────────────────
    _register_page_routes(app)
    _add_template_filters(app)

    # ── Startup / shutdown hooks ───────────────────────────────────────────────
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.APP_ENV)
        await _seed_initial_data()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("%s shutting down.", settings.APP_NAME)

    # ── Exception handlers ─────────────────────────────────────────────────────
    _register_exception_handlers(app)

    return app


def _register_page_routes(app: VayuAPI) -> None:
    """Register simple HTML page routes that don't belong to a feature controller."""
    from vayuapi import Request, Depends
    from config.database import get_db
    from middlewares.auth import get_current_user_optional

    @app.get("/login")
    async def login_page(request: Request):
        return templates.TemplateResponse("auth/login.html", {"request": request, "settings": settings})

    @app.get("/register")
    async def register_page(request: Request):
        return templates.TemplateResponse("auth/register.html", {"request": request, "settings": settings})

    @app.get("/forgot-password")
    async def forgot_password_page(request: Request):
        return templates.TemplateResponse("auth/forgot_password.html", {"request": request, "settings": settings})

    @app.get("/reset-password")
    async def reset_password_page(request: Request):
        return templates.TemplateResponse("auth/reset_password.html", {"request": request, "settings": settings})

    @app.get("/verify-email")
    async def verify_email_page(request: Request):
        return templates.TemplateResponse("auth/verify_email.html", {"request": request, "settings": settings})


def _register_exception_handlers(app: VayuAPI) -> None:
    """Register global error page handlers."""
    from vayuapi import Request, HTTPException
    from vayuapi.response import JSONResponse

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        if request.url.path.startswith("/api"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "settings": settings},
            status_code=404,
        )

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server error: %s", exc)
        if request.url.path.startswith("/api"):
            return JSONResponse({"detail": "Internal server error"}, status_code=500)
        return templates.TemplateResponse(
            "errors/500.html",
            {"request": request, "settings": settings},
            status_code=500,
        )


async def _seed_initial_data() -> None:
    """Seed roles, default admin, and sample products on first run."""
    from config.database import AsyncSessionLocal
    from models.user import Role, User, UserRole
    from models.product import Category, Brand, Product, ProductVariant, ProductStatus
    from utils.security import hash_password
    from utils.slugify import make_slug
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        try:
            # Seed roles
            role_defs = [
                ("super_admin", "Full system access"),
                ("admin", "Administrative access"),
                ("inventory_manager", "Inventory management"),
                ("order_manager", "Order management"),
                ("customer_support", "Customer support"),
                ("customer", "Regular customer"),
            ]
            for role_name, role_desc in role_defs:
                exists = (await session.execute(
                    select(Role).where(Role.name == role_name)
                )).scalar_one_or_none()
                if not exists:
                    session.add(Role(name=role_name, description=role_desc))

            await session.flush()

            # Seed super admin
            admin_exists = (await session.execute(
                select(User).where(User.email == settings.SUPER_ADMIN_EMAIL)
            )).scalar_one_or_none()

            if not admin_exists:
                admin_user = User(
                    first_name="Super",
                    last_name="Admin",
                    email=settings.SUPER_ADMIN_EMAIL,
                    password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
                    is_active=True,
                    is_verified=True,
                    is_staff=True,
                )
                session.add(admin_user)
                await session.flush()

                super_admin_role = (await session.execute(
                    select(Role).where(Role.name == "super_admin")
                )).scalar_one_or_none()

                if super_admin_role:
                    session.add(UserRole(user_id=admin_user.id, role_id=super_admin_role.id))

            # Seed brand
            brand_exists = (await session.execute(
                select(Brand).where(Brand.name == "Amrit One")
            )).scalar_one_or_none()

            if not brand_exists:
                brand = Brand(name="Amrit One", slug="amrit-one", is_active=True)
                session.add(brand)

            # Seed categories
            categories = [
                ("Organic Powders", "organic-powders", "Pure organic herbal and superfood powders"),
                ("Ghee & Dairy", "ghee-dairy", "Authentic desi cow and buffalo ghee"),
                ("Ayurvedic Herbs", "ayurvedic-herbs", "Traditional Ayurvedic herbs and botanicals"),
            ]
            cat_ids = {}
            for cat_name, cat_slug, cat_desc in categories:
                cat_exists = (await session.execute(
                    select(Category).where(Category.slug == cat_slug)
                )).scalar_one_or_none()
                if not cat_exists:
                    cat = Category(name=cat_name, slug=cat_slug, description=cat_desc, is_active=True)
                    session.add(cat)
                    await session.flush()
                    cat_ids[cat_slug] = cat.id
                else:
                    cat_ids[cat_slug] = cat_exists.id

            # Seed initial products
            initial_products = [
                {
                    "name": "Organic Moringa Powder",
                    "slug": "organic-moringa-powder",
                    "short_description": "Premium quality organic Moringa leaf powder — nature's multivitamin.",
                    "description": "Our Organic Moringa Powder is made from sun-dried, organically cultivated Moringa oleifera leaves. Rich in vitamins, minerals, and antioxidants, it supports immunity, energy, and overall wellness.",
                    "ingredients": "100% Pure Organic Moringa (Moringa oleifera) Leaf Powder",
                    "benefits": "Boosts immunity, supports energy levels, rich in vitamins A, C & E, excellent source of plant-based protein, anti-inflammatory properties.",
                    "usage_instructions": "Mix 1 tsp in warm water, smoothies, or juices. Best consumed in the morning.",
                    "storage_instructions": "Store in a cool, dry place away from direct sunlight. Use within 12 months of opening.",
                    "category_slug": "organic-powders",
                    "is_featured": True,
                    "is_best_seller": True,
                    "is_new_arrival": False,
                    "meta_title": "Organic Moringa Powder | Amrit One",
                    "variants": [
                        {"size": "100g", "sku": "AMP-MOR-100", "price": 199, "mrp": 249, "weight_grams": 100, "stock": 50},
                        {"size": "200g", "sku": "AMP-MOR-200", "price": 349, "mrp": 449, "weight_grams": 200, "stock": 40},
                        {"size": "400g", "sku": "AMP-MOR-400", "price": 649, "mrp": 849, "weight_grams": 400, "stock": 30},
                    ],
                },
                {
                    "name": "Organic Amla Powder",
                    "slug": "organic-amla-powder",
                    "short_description": "100% pure Indian Gooseberry powder — nature's vitamin C powerhouse.",
                    "description": "Amla (Indian Gooseberry) is one of Ayurveda's most revered superfoods. Our organic Amla Powder is made from fresh, sun-dried amla fruits without any additives.",
                    "ingredients": "100% Pure Organic Amla (Phyllanthus emblica) Fruit Powder",
                    "benefits": "Highest natural source of Vitamin C, promotes hair growth, strengthens immunity, supports digestion, powerful antioxidant.",
                    "usage_instructions": "Mix 1 tsp in water or juice daily. Can also be added to hair packs.",
                    "storage_instructions": "Store in an airtight container in a cool, dry place.",
                    "category_slug": "organic-powders",
                    "is_featured": True,
                    "is_best_seller": False,
                    "is_new_arrival": True,
                    "meta_title": "Organic Amla Powder | Amrit One",
                    "variants": [
                        {"size": "100g", "sku": "AMP-AML-100", "price": 149, "mrp": 199, "weight_grams": 100, "stock": 60},
                        {"size": "200g", "sku": "AMP-AML-200", "price": 279, "mrp": 369, "weight_grams": 200, "stock": 45},
                        {"size": "400g", "sku": "AMP-AML-400", "price": 529, "mrp": 699, "weight_grams": 400, "stock": 25},
                    ],
                },
                {
                    "name": "Organic Aparajita Powder",
                    "slug": "organic-aparajita-powder",
                    "short_description": "Butterfly pea flower powder — a rare Ayurvedic botanical.",
                    "description": "Aparajita (Clitoria ternatea) is a sacred Ayurvedic herb known for its cognitive and adaptogenic properties. Our pure powder is crafted from organically grown flowers.",
                    "ingredients": "100% Pure Organic Aparajita (Clitoria ternatea) Flower Powder",
                    "benefits": "Enhances memory and focus, reduces stress, promotes hair health, supports nervous system.",
                    "usage_instructions": "Add 1/2 tsp to warm milk or herbal tea. Best taken before bedtime.",
                    "storage_instructions": "Store away from moisture and direct sunlight.",
                    "category_slug": "ayurvedic-herbs",
                    "is_featured": False,
                    "is_best_seller": False,
                    "is_new_arrival": True,
                    "meta_title": "Organic Aparajita Powder | Amrit One",
                    "variants": [
                        {"size": "100g", "sku": "AMP-APJ-100", "price": 229, "mrp": 299, "weight_grams": 100, "stock": 35},
                        {"size": "200g", "sku": "AMP-APJ-200", "price": 429, "mrp": 549, "weight_grams": 200, "stock": 20},
                    ],
                },
                {
                    "name": "Desi Cow Ghee",
                    "slug": "desi-cow-ghee",
                    "short_description": "Pure A2 Desi Cow Ghee made using traditional Vedic bilona method.",
                    "description": "Our Desi Cow Ghee is prepared using the ancient Vedic bilona churning method from A2 milk of indigenous Gir cows. Each batch is slow-cooked to perfection, preserving all the therapeutic properties.",
                    "ingredients": "Pure A2 Gir Cow Milk",
                    "benefits": "Strengthens immunity, aids digestion, lubricates joints, supports brain health, rich in fat-soluble vitamins A, D, E & K.",
                    "usage_instructions": "Use 1-2 tsp for cooking or add to warm rice/roti. Can also be taken directly.",
                    "storage_instructions": "Store at room temperature in a sealed container. No refrigeration required.",
                    "category_slug": "ghee-dairy",
                    "is_featured": True,
                    "is_best_seller": True,
                    "is_new_arrival": False,
                    "meta_title": "Pure Desi Cow Ghee A2 | Amrit One",
                    "variants": [
                        {"size": "250ml", "sku": "AMP-DCG-250", "price": 449, "mrp": 549, "weight_grams": 250, "stock": 30},
                        {"size": "500ml", "sku": "AMP-DCG-500", "price": 849, "mrp": 1049, "weight_grams": 500, "stock": 25},
                        {"size": "1L", "sku": "AMP-DCG-1000", "price": 1599, "mrp": 1999, "weight_grams": 1000, "stock": 15},
                    ],
                },
                {
                    "name": "Desi Buffalo Ghee",
                    "slug": "desi-buffalo-ghee",
                    "short_description": "Rich and creamy pure Buffalo Ghee made from fresh buffalo milk.",
                    "description": "Made from the milk of grass-fed Indian buffaloes, our Desi Buffalo Ghee is richer in fat and carries a distinctive rich aroma. Prepared using traditional churning methods.",
                    "ingredients": "Pure Buffalo Milk",
                    "benefits": "Rich in omega fatty acids, supports bone health, high energy source, aids in absorption of fat-soluble nutrients.",
                    "usage_instructions": "Ideal for cooking at high temperatures. Use 1-2 tsp per serving.",
                    "storage_instructions": "Store at room temperature. Consume within 12 months.",
                    "category_slug": "ghee-dairy",
                    "is_featured": False,
                    "is_best_seller": True,
                    "is_new_arrival": False,
                    "meta_title": "Pure Desi Buffalo Ghee | Amrit One",
                    "variants": [
                        {"size": "250ml", "sku": "AMP-DBG-250", "price": 399, "mrp": 499, "weight_grams": 250, "stock": 25},
                        {"size": "500ml", "sku": "AMP-DBG-500", "price": 749, "mrp": 949, "weight_grams": 500, "stock": 20},
                        {"size": "1L", "sku": "AMP-DBG-1000", "price": 1399, "mrp": 1799, "weight_grams": 1000, "stock": 10},
                    ],
                },
            ]

            brand_obj = (await session.execute(
                select(Brand).where(Brand.slug == "amrit-pure")
            )).scalar_one_or_none()

            from decimal import Decimal
            for p_data in initial_products:
                product_exists = (await session.execute(
                    select(Product).where(Product.slug == p_data["slug"])
                )).scalar_one_or_none()

                if not product_exists:
                    cat_id = cat_ids.get(p_data["category_slug"])
                    product = Product(
                        name=p_data["name"],
                        slug=p_data["slug"],
                        short_description=p_data["short_description"],
                        description=p_data["description"],
                        ingredients=p_data["ingredients"],
                        benefits=p_data["benefits"],
                        usage_instructions=p_data["usage_instructions"],
                        storage_instructions=p_data["storage_instructions"],
                        category_id=cat_id,
                        brand_id=brand_obj.id if brand_obj else None,
                        status=ProductStatus.PUBLISHED,
                        is_featured=p_data["is_featured"],
                        is_best_seller=p_data["is_best_seller"],
                        is_new_arrival=p_data["is_new_arrival"],
                        meta_title=p_data["meta_title"],
                    )
                    session.add(product)
                    await session.flush()

                    for v in p_data["variants"]:
                        discount = Decimal(str(round((1 - v["price"] / v["mrp"]) * 100, 2)))
                        session.add(ProductVariant(
                            product_id=product.id,
                            size=v["size"],
                            sku=v["sku"],
                            price=Decimal(str(v["price"])),
                            mrp=Decimal(str(v["mrp"])),
                            discount_percent=discount,
                            gst_percent=Decimal("5.00"),
                            stock_quantity=v["stock"],
                            low_stock_alert=10,
                            weight_grams=v["weight_grams"],
                        ))

            await session.commit()
            logger.info("Database seeded successfully")

        except Exception as exc:
            await session.rollback()
            logger.warning("Seeding skipped (likely already seeded): %s", exc)


# ── Jinja2 custom filters ──────────────────────────────────────────────────────
# Filters are registered in config/templates.py on the shared instance.

def _add_template_filters(app: VayuAPI) -> None:
    pass  # no-op: filters already live on the shared templates instance


# ── Application instance ───────────────────────────────────────────────────────
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
