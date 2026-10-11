"""Product Review ORM model."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from models.base import TimestampMixin

if TYPE_CHECKING:
    from models.user import User
    from models.product import Product


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_product_id", "product_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–5
    title: Mapped[Optional[str]] = mapped_column(String(255))
    body: Mapped[Optional[str]] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)

    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="reviews")
