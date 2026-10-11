"""Pydantic schemas for Product, Variant, Category."""

from __future__ import annotations
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from models.product import ProductStatus, VariantStatus


class CategoryResponseSchema(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    image: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class BrandResponseSchema(BaseModel):
    id: int
    name: str
    slug: str
    logo: Optional[str]

    model_config = {"from_attributes": True}


class TagResponseSchema(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


class VariantResponseSchema(BaseModel):
    id: int
    size: str
    sku: str
    price: Decimal
    mrp: Decimal
    discount_percent: Decimal
    gst_percent: Decimal
    stock_quantity: int
    low_stock_alert: int
    weight_grams: int
    status: VariantStatus
    is_in_stock: bool
    is_low_stock: bool

    model_config = {"from_attributes": True}


class ProductImageResponseSchema(BaseModel):
    id: int
    image_url: str
    alt_text: Optional[str]
    is_primary: bool
    sort_order: int

    model_config = {"from_attributes": True}


class ProductListSchema(BaseModel):
    id: int
    name: str
    slug: str
    short_description: Optional[str]
    status: ProductStatus
    is_featured: bool
    is_best_seller: bool
    is_new_arrival: bool
    avg_rating: Decimal
    review_count: int
    primary_image: Optional[str]
    category: Optional[CategoryResponseSchema]
    variants: List[VariantResponseSchema]

    model_config = {"from_attributes": True}


class ProductDetailSchema(ProductListSchema):
    description: Optional[str]
    ingredients: Optional[str]
    benefits: Optional[str]
    usage_instructions: Optional[str]
    storage_instructions: Optional[str]
    specifications: Optional[str]
    faqs: Optional[str]
    brand: Optional[BrandResponseSchema]
    tags: List[TagResponseSchema]
    images: List[ProductImageResponseSchema]
    meta_title: Optional[str]
    meta_description: Optional[str]
    meta_keywords: Optional[str]
    og_title: Optional[str]
    og_description: Optional[str]
    og_image: Optional[str]

    model_config = {"from_attributes": True}


class ProductCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)
    slug: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    ingredients: Optional[str] = None
    benefits: Optional[str] = None
    usage_instructions: Optional[str] = None
    storage_instructions: Optional[str] = None
    specifications: Optional[str] = None
    faqs: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    status: ProductStatus = ProductStatus.DRAFT
    is_featured: bool = False
    is_best_seller: bool = False
    is_new_arrival: bool = False
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = Field(None, max_length=500)
    tag_ids: List[int] = []
