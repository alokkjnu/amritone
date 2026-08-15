"""Pydantic schemas for Cart."""

from __future__ import annotations
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class CartAddSchema(BaseModel):
    product_id: int
    variant_id: int
    quantity: int = Field(1, ge=1, le=100)


class CartUpdateSchema(BaseModel):
    quantity: int = Field(..., ge=0, le=100)


class CartItemResponseSchema(BaseModel):
    id: int
    product_id: int
    variant_id: int
    quantity: int
    product_name: str
    variant_size: str
    unit_price: Decimal
    mrp: Decimal
    total_price: Decimal
    product_image: Optional[str]
    is_in_stock: bool

    model_config = {"from_attributes": True}


class CartResponseSchema(BaseModel):
    id: int
    items: List[CartItemResponseSchema]
    subtotal: Decimal
    total_items: int

    model_config = {"from_attributes": True}


class CouponApplySchema(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
