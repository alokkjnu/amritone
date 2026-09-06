"""Media ORM model."""

from __future__ import annotations
from typing import Optional
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from config.database import Base
from models.base import TimestampMixin


class Media(Base, TimestampMixin):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255))
    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
