"""
Order, OrderItem, and OrderStatusHistory ORM models.
"""

from __future__ import annotations

import enum
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, Enum, ForeignKey, Index, Integer,
    Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base
from models.base import TimestampMixin

if TYPE_CHECKING:
    from models.user import User, UserAddress
    from models.product import Product, ProductVariant
    from models.coupon import Coupon
    from models.return_request import ReturnRequest


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, enum.Enum):
    COD = "cod"
    RAZORPAY = "razorpay"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_order_number", "order_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # Pricing
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    shipping_charge: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Coupon
    coupon_id: Mapped[Optional[int]] = mapped_column(ForeignKey("coupons.id", ondelete="SET NULL"))
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50))

    # Status
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.COD)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(200))

    # Addresses (snapshot at time of order)
    billing_name: Mapped[str] = mapped_column(String(200), nullable=False)
    billing_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_address: Mapped[str] = mapped_column(Text, nullable=False)
    billing_city: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_state: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    billing_country: Mapped[str] = mapped_column(String(100), default="India")

    shipping_name: Mapped[str] = mapped_column(String(200), nullable=False)
    shipping_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_state: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    shipping_country: Mapped[str] = mapped_column(String(100), default="India")

    # Tracking
    tracking_number: Mapped[Optional[str]] = mapped_column(String(200))
    tracking_url: Mapped[Optional[str]] = mapped_column(String(500))
    courier_name: Mapped[Optional[str]] = mapped_column(String(200))

    # Notes
    customer_notes: Mapped[Optional[str]] = mapped_column(Text)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    status_history: Mapped[List["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory", back_populates="order", cascade="all, delete-orphan"
    )
    coupon: Mapped[Optional["Coupon"]] = relationship("Coupon")
    return_requests: Mapped[List["ReturnRequest"]] = relationship(
        "ReturnRequest", back_populates="order"
    )


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"))

    # Snapshot at time of order
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    variant_size: Mapped[str] = mapped_column(String(50), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    mrp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_image: Mapped[Optional[str]] = mapped_column(String(500))

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="order_items")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", back_populates="order_items")


class OrderStatusHistory(Base, TimestampMixin):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    order: Mapped["Order"] = relationship("Order", back_populates="status_history")
