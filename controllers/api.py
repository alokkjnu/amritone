"""General JSON API endpoints — newsletter, reviews, notifications, search."""

from typing import Optional
from vayuapi import VayuAPI, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.database import get_db
from middlewares.auth import get_current_user, get_current_user_optional
from models.user import User
from models.newsletter import NewsletterSubscriber
from models.review import Review
from models.notification import Notification

router = VayuAPI()


@router.post("/api/newsletter/subscribe")
async def subscribe_newsletter(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    existing = (await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )).scalar_one_or_none()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.add(existing)
            await db.flush()
        return {"message": "You are now subscribed!"}

    db.add(NewsletterSubscriber(email=email))
    await db.flush()
    return {"message": "Subscribed successfully!"}


@router.post("/api/reviews")
async def submit_review(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body = await request.json()
    product_id = body.get("product_id")
    rating = body.get("rating")
    if not product_id or not rating or not (1 <= int(rating) <= 5):
        raise HTTPException(status_code=400, detail="Invalid review data")

    db.add(Review(
        product_id=int(product_id),
        user_id=current_user.id,
        rating=int(rating),
        title=body.get("title"),
        body=body.get("body"),
        is_approved=False,
    ))
    await db.flush()
    return {"message": "Review submitted and awaiting approval"}


@router.get("/api/notifications")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
    )
    notifications = list((await db.execute(stmt)).scalars().all())
    return {
        "notifications": [
            {
                "id": n.id, "title": n.title, "message": n.message,
                "is_read": n.is_read, "type": n.notification_type,
                "link_url": n.link_url, "created_at": str(n.created_at),
            }
            for n in notifications
        ]
    }


@router.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = await db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.add(notif)
    await db.flush()
    return {"message": "Marked as read"}


@router.post("/api/return-request")
async def submit_return_request(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from models.return_request import ReturnRequest, ReturnReason
    from repositories.order import OrderRepository
    body = await request.json()
    order_id = body.get("order_id")
    reason = body.get("reason")
    description = body.get("description")

    order_repo = OrderRepository(db)
    order = await order_repo.get_by_id(int(order_id))
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    db.add(ReturnRequest(
        order_id=order.id,
        user_id=current_user.id,
        reason=ReturnReason(reason),
        description=description,
    ))
    await db.flush()
    return {"message": "Return request submitted"}
