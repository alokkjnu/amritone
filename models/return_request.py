"""ReturnRequest ORM model."""

from __future__ import annotations
import enum
from typing import Optional
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from models.base import TimestampMixin


class ReturnStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    RECEIVED = "received"
    REFUNDED = "refunded"


class ReturnReason(str, enum.Enum):
    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    QUALITY_ISSUE = "quality_issue"
    OTHER = "other"


class ReturnRequest(Base, TimestampMixin):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[ReturnReason] = mapped_column(Enum(ReturnReason), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ReturnStatus] = mapped_column(Enum(ReturnStatus), default=ReturnStatus.REQUESTED)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)
    refund_amount: Mapped[Optional[str]] = mapped_column(String(20))

    order: Mapped["Order"] = relationship("Order", back_populates="return_requests")
