"""Newsletter Subscriber ORM model."""

from __future__ import annotations
from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from config.database import Base
from models.base import TimestampMixin


class NewsletterSubscriber(Base, TimestampMixin):
    __tablename__ = "newsletter_subscribers"
    __table_args__ = (Index("ix_newsletter_email", "email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
