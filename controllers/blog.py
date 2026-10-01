"""Public blog routes."""

from typing import Optional
from vayuapi import VayuAPI, Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.settings import settings
from middlewares.auth import get_current_user_optional
from models.blog import Blog, BlogCategory, BlogStatus
from models.user import User
from sqlalchemy.orm import selectinload

router = VayuAPI()
from config.templates import templates


@router.get("/blog")
async def blog_list(
    request: Request,
    page: int = 1,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    page_size = 9
    stmt = select(Blog).options(selectinload(Blog.category)).where(Blog.status == BlogStatus.PUBLISHED)
    if category:
        cat_stmt = select(BlogCategory).where(BlogCategory.slug == category)
        cat = (await db.execute(cat_stmt)).scalar_one_or_none()
        if cat:
            stmt = stmt.where(Blog.category_id == cat.id)

    from sqlalchemy import func
    total = (await db.execute(select(func.count()).select_from(
        select(Blog).where(Blog.status == BlogStatus.PUBLISHED).subquery()
    ))).scalar_one()
    stmt = stmt.order_by(Blog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    blogs = list((await db.execute(stmt)).scalars().all())

    categories = list((await db.execute(
        select(BlogCategory).where(BlogCategory.is_active == True)
    )).scalars().all())

    return templates.TemplateResponse("shop/blog/list.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "blogs": blogs,
        "categories": categories, "total": total,
        "page": page, "total_pages": (total + page_size - 1) // page_size,
    })


@router.get("/blog/{slug}")
async def blog_detail(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    stmt = select(Blog).options(selectinload(Blog.category)).where(
        Blog.slug == slug, Blog.status == BlogStatus.PUBLISHED
    )
    blog = (await db.execute(stmt)).scalar_one_or_none()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog post not found")

    # Increment view count
    blog.view_count += 1
    db.add(blog)
    await db.flush()

    return templates.TemplateResponse("shop/blog/detail.html", {
        "request": request, "current_user": current_user,
        "settings": settings, "blog": blog,
    })
