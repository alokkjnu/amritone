"""Blog and BlogCategory ORM models."""

from __future__ import annotations
import enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base
from models.base import TimestampMixin


class BlogStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


blog_tags = Table(
    "blog_tags",
    Base.metadata,
    Column("blog_id", Integer, ForeignKey("blogs.id", ondelete="CASCADE")),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE")),
)


class BlogCategory(Base, TimestampMixin):
    __tablename__ = "blog_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    blogs: Mapped[List["Blog"]] = relationship("Blog", back_populates="category")


class Blog(Base, TimestampMixin):
    __tablename__ = "blogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(550), unique=True, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(String(1000))
    content: Mapped[Optional[str]] = mapped_column(Text)
    featured_image: Mapped[Optional[str]] = mapped_column(String(500))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blog_categories.id", ondelete="SET NULL"))
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[BlogStatus] = mapped_column(Enum(BlogStatus), default=BlogStatus.DRAFT)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[Optional[str]] = mapped_column(String(255))
    meta_description: Mapped[Optional[str]] = mapped_column(Text)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String(500))

    category: Mapped[Optional["BlogCategory"]] = relationship("BlogCategory", back_populates="blogs")
