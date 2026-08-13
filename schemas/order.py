"""Pydantic schemas for Order and Checkout."""

from __future__ import annotations
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from models.order import OrderStatus, PaymentMethod, PaymentStatus


class CheckoutAddressSchema(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    address_line1: str = Field(..., min_length=5, max_length=500)
    address_line2: Optional[str] = Field(None, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., pattern=r"^[0-9]{6}$")
    country: str = "India"


class CheckoutSchema(BaseModel):
    billing_address: CheckoutAddressSchema
    shipping_address: CheckoutAddressSchema
    same_as_billing: bool = False
    payment_method: PaymentMethod = PaymentMethod.COD
    coupon_code: Optional[str] = None
    customer_notes: Optional[str] = Field(None, max_length=1000)


class OrderItemResponseSchema(BaseModel):
    id: int
    product_name: str
    variant_size: str
    sku: str
    quantity: int
    unit_price: Decimal
    mrp: Decimal
    total_price: Decimal
    product_image: Optional[str]

    model_config = {"from_attributes": True}


class OrderResponseSchema(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    subtotal: Decimal
    discount_amount: Decimal
    shipping_charge: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    payment_method: str
    payment_status: str
    coupon_code: Optional[str]
    tracking_number: Optional[str]
    courier_name: Optional[str]
    customer_notes: Optional[str]
    items: List[OrderItemResponseSchema]
    created_at: str

    model_config = {"from_attributes": True}


class OrderStatusUpdateSchema(BaseModel):
    status: OrderStatus
    comment: Optional[str] = None
    tracking_number: Optional[str] = None
    courier_name: Optional[str] = None
    tracking_url: Optional[str] = None


class PaymentStatusUpdateSchema(BaseModel):
    payment_status: PaymentStatus
    payment_reference: Optional[str] = None
