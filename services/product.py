"""Product, Category, and Variant service."""

from __future__ import annotations
import json
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from models.product import Product, ProductVariant, ProductImage, Category, Brand, Tag, ProductStatus
from repositories.product import ProductRepository, CategoryRepository, VariantRepository
from schemas.product import ProductCreateSchema
from utils.slugify import make_slug
from utils.pagination import PaginatedResult
from vayuapi import HTTPException

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)
        self.variant_repo = VariantRepository(session)

    async def get_product_by_slug(self, slug: str) -> Product:
        product = await self.product_repo.get_by_slug(slug)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 12,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_featured: Optional[bool] = None,
        is_best_seller: Optional[bool] = None,
        is_new_arrival: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaginatedResult[Product]:
        items, total = await self.product_repo.get_paginated(
            page=page,
            page_size=page_size,
            category_id=category_id,
            search=search,
            min_price=min_price,
            max_price=max_price,
            is_featured=is_featured,
            is_best_seller=is_best_seller,
            is_new_arrival=is_new_arrival,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PaginatedResult(items=items, total=total, page=page, page_size=page_size)

    async def get_homepage_data(self) -> dict:
        """Return all product sets needed for the homepage."""
        featured = await self.product_repo.get_featured(limit=8)
        best_sellers = await self.product_repo.get_best_sellers(limit=8)
        new_arrivals = await self.product_repo.get_new_arrivals(limit=8)
        categories = await self.category_repo.get_active()
        return {
            "featured_products": featured,
            "best_sellers": best_sellers,
            "new_arrivals": new_arrivals,
            "categories": categories,
        }

    async def create_product(self, data: ProductCreateSchema) -> Product:
        slug = data.slug or make_slug(data.name)
        existing = await self.product_repo.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{int(__import__('time').time())}"

        product = await self.product_repo.create(
            name=data.name,
            slug=slug,
            short_description=data.short_description,
            description=data.description,
            ingredients=data.ingredients,
            benefits=data.benefits,
            usage_instructions=data.usage_instructions,
            storage_instructions=data.storage_instructions,
            specifications=data.specifications,
            faqs=data.faqs,
            category_id=data.category_id,
            brand_id=data.brand_id,
            status=data.status,
            is_featured=data.is_featured,
            is_best_seller=data.is_best_seller,
            is_new_arrival=data.is_new_arrival,
            meta_title=data.meta_title,
            meta_description=data.meta_description,
            meta_keywords=data.meta_keywords,
        )

        if data.tag_ids:
            from sqlalchemy import select
            tags = list((await self.session.execute(
                select(Tag).where(Tag.id.in_(data.tag_ids))
            )).scalars().all())
            product.tags = tags
            await self.session.flush()

        logger.info("Product created: %s (id=%d)", product.name, product.id)
        return product

    async def update_product_rating(self, product_id: int) -> None:
        """Recalculate and persist avg_rating and review_count."""
        from sqlalchemy import func, select
        from models.review import Review
        stmt = select(
            func.avg(Review.rating).label("avg"),
            func.count(Review.id).label("cnt"),
        ).where(Review.product_id == product_id, Review.is_approved == True)
        row = (await self.session.execute(stmt)).one()
        product = await self.product_repo.get_by_id(product_id)
        if product:
            from decimal import Decimal
            await self.product_repo.update(
                product,
                avg_rating=Decimal(str(row.avg or 0)).quantize(Decimal("0.01")),
                review_count=row.cnt or 0,
            )

    async def get_categories(self) -> List[Category]:
        return await self.category_repo.get_active()

    async def get_low_stock_variants(self) -> List[ProductVariant]:
        return await self.variant_repo.get_low_stock()
