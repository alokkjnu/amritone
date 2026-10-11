"""
Product, Category, Brand, Tag, Variant, and Image ORM models.
"""

from __future__ import annotations

import enum
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base
from models.base import TimestampMixin

if TYPE_CHECKING:
    from models.order import OrderItem
    from models.review import Review
    from models.cart import CartItem
    from models.wishlist import WishlistItem


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class VariantStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


# Association table: product ↔ tag
from sqlalchemy import Table, Column
product_tags = Table(
    "product_tags",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE")),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE")),
)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image: Mapped[Optional[str]] = mapped_column(String(500))
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[Optional[str]] = mapped_column(String(255))
    meta_description: Mapped[Optional[str]] = mapped_column(Text)

    parent: Mapped[Optional["Category"]] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[List["Category"]] = relationship(
        "Category", back_populates="parent"
    )
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    logo: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    products: Mapped[List["Product"]] = relationship("Product", back_populates="brand")


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    products: Mapped[List["Product"]] = relationship(
        "Product", secondary=product_tags, back_populates="tags"
    )


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_slug", "slug"),
        Index("ix_products_status", "status"),
        Index("ix_products_category_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(550), unique=True, nullable=False)
    short_description: Mapped[Optional[str]] = mapped_column(String(1000))
    description: Mapped[Optional[str]] = mapped_column(Text)
    ingredients: Mapped[Optional[str]] = mapped_column(Text)
    benefits: Mapped[Optional[str]] = mapped_column(Text)
    usage_instructions: Mapped[Optional[str]] = mapped_column(Text)
    storage_instructions: Mapped[Optional[str]] = mapped_column(Text)
    specifications: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    faqs: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    brand_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL")
    )

    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.DRAFT
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_best_seller: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new_arrival: Mapped[bool] = mapped_column(Boolean, default=False)

    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(255))
    meta_description: Mapped[Optional[str]] = mapped_column(Text)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String(500))
    canonical_url: Mapped[Optional[str]] = mapped_column(String(500))
    og_title: Mapped[Optional[str]] = mapped_column(String(255))
    og_description: Mapped[Optional[str]] = mapped_column(Text)
    og_image: Mapped[Optional[str]] = mapped_column(String(500))
    twitter_card: Mapped[Optional[str]] = mapped_column(String(50))
    twitter_title: Mapped[Optional[str]] = mapped_column(String(255))
    twitter_description: Mapped[Optional[str]] = mapped_column(Text)

    # Aggregates (updated via triggers/services)
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    total_sold: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="products"
    )
    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="products")
    tags: Mapped[List["Tag"]] = relationship(
        "Tag", secondary=product_tags, back_populates="products"
    )
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage", back_populates="product", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="product")
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="product"
    )

    @property
    def primary_image(self) -> Optional[str]:
        primary = next((img for img in self.images if img.is_primary), None)
        if primary:
            return primary.image_url
        return self.images[0].image_url if self.images else None


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size"),
        Index("ix_product_variants_sku", "sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    size: Mapped[str] = mapped_column(String(50), nullable=False)  # 100g, 200g, 400g
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    barcode: Mapped[Optional[str]] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    mrp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("5.00"))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_alert: Mapped[int] = mapped_column(Integer, default=10)
    weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VariantStatus] = mapped_column(
        Enum(VariantStatus), default=VariantStatus.ACTIVE
    )

    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="variant"
    )
    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem", back_populates="variant"
    )
    inventory_logs: Mapped[List["InventoryLog"]] = relationship(
        "InventoryLog", back_populates="variant"
    )

    @property
    def discount_amount(self) -> Decimal:
        return self.mrp - self.price

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.low_stock_alert

    @property
    def is_in_stock(self) -> bool:
        return self.stock_quantity > 0


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship("Product", back_populates="images")
