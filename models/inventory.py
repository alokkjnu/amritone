"""InventoryLog ORM model."""

from __future__ import annotations
import enum
from typing import Optional
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from models.base import TimestampMixin


class InventoryAction(str, enum.Enum):
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    ADJUSTMENT = "adjustment"
    ORDER_RESERVED = "order_reserved"
    ORDER_RELEASED = "order_released"
    RETURN = "return"


class InventoryLog(Base, TimestampMixin):
    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"))
    action: Mapped[InventoryAction] = mapped_column(Enum(InventoryAction), nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    performed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="inventory_logs")
