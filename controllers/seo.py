"""SEO routes — sitemap.xml, robots.txt."""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from vayuapi import VayuAPI, Request, Depends
from vayuapi.response import Response

from config.database import get_db
from config.settings import settings
from models.product import Product, ProductStatus
from models.blog import Blog, BlogStatus

router = VayuAPI()


@router.get("/sitemap.xml")
async def sitemap(request: Request, db: AsyncSession = Depends(get_db)):
    base = settings.BASE_URL
    products = list((await db.execute(
        select(Product.slug, Product.updated_at).where(Product.status == ProductStatus.PUBLISHED)
    )).all())
    blogs = list((await db.execute(
        select(Blog.slug, Blog.updated_at).where(Blog.status == BlogStatus.PUBLISHED)
    )).all())

    urls = [
        f"<url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>",
        f"<url><loc>{base}/shop</loc><changefreq>daily</changefreq><priority>0.9</priority></url>",
        f"<url><loc>{base}/blog</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>",
    ]
    for p in products:
        urls.append(
            f"<url><loc>{base}/product/{p.slug}</loc>"
            f"<lastmod>{p.updated_at.strftime('%Y-%m-%d')}</lastmod>"
            f"<changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )
    for b in blogs:
        urls.append(
            f"<url><loc>{base}/blog/{b.slug}</loc>"
            f"<lastmod>{b.updated_at.strftime('%Y-%m-%d')}</lastmod>"
            f"<changefreq>monthly</changefreq><priority>0.6</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt")
async def robots(request: Request):
    base = settings.BASE_URL
    content = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/
Disallow: /account/
Sitemap: {base}/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")
