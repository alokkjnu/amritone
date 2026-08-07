"""Order service — checkout, status management, invoice generation."""

from __future__ import annotations
import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from models.order import Order, OrderItem, OrderStatusHistory, OrderStatus, PaymentMethod
from models.inventory import InventoryLog, InventoryAction
from repositories.order import OrderRepository
from repositories.cart import CartRepository
from repositories.coupon import CouponRepository
from repositories.product import VariantRepository
from schemas.order import CheckoutSchema, OrderStatusUpdateSchema
from utils.order_number import generate_order_number
from utils.email import send_email
from vayuapi import HTTPException

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.order_repo = OrderRepository(session)
        self.cart_repo = CartRepository(session)
        self.coupon_repo = CouponRepository(session)
        self.variant_repo = VariantRepository(session)

    async def checkout(self, user_id: int, data: CheckoutSchema) -> Order:
        """Create order from cart, apply coupon, deduct stock."""
        cart = await self.cart_repo.get_cart_for_user(user_id)
        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Validate stock and compute totals
        subtotal = Decimal("0.00")
        gst_total = Decimal("0.00")
        order_items_data = []

        for item in cart.items:
            variant = item.variant
            product = item.product
            if not variant or not product:
                continue
            if variant.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product.name} ({variant.size})",
                )
            line_total = variant.price * item.quantity
            gst_amount = line_total * (variant.gst_percent / 100)
            subtotal += line_total
            gst_total += gst_amount
            order_items_data.append({
                "product_id": product.id,
                "variant_id": variant.id,
                "product_name": product.name,
                "variant_size": variant.size,
                "sku": variant.sku,
                "quantity": item.quantity,
                "unit_price": variant.price,
                "mrp": variant.mrp,
                "gst_percent": variant.gst_percent,
                "total_price": line_total,
                "product_image": product.primary_image if hasattr(product, "primary_image") else None,
            })

        # Coupon
        discount_amount = Decimal("0.00")
        coupon = None
        if data.coupon_code:
            coupon, discount_amount = await self._apply_coupon(
                data.coupon_code, user_id, subtotal
            )

        shipping_charge = Decimal("0.00") if subtotal >= Decimal("500") else Decimal("50.00")
        total_amount = subtotal + gst_total + shipping_charge - discount_amount

        # Shipping address
        ship = data.billing_address if data.same_as_billing else data.shipping_address
        bill = data.billing_address

        order = await self.order_repo.create(
            order_number=generate_order_number(),
            user_id=user_id,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_charge=shipping_charge,
            gst_amount=gst_total,
            total_amount=total_amount,
            coupon_id=coupon.id if coupon else None,
            coupon_code=data.coupon_code.upper() if data.coupon_code else None,
            payment_method=data.payment_method,
            customer_notes=data.customer_notes,
            # Billing snapshot
            billing_name=bill.full_name,
            billing_phone=bill.phone,
            billing_address=f"{bill.address_line1}, {bill.address_line2 or ''}".strip(", "),
            billing_city=bill.city,
            billing_state=bill.state,
            billing_pincode=bill.pincode,
            billing_country=bill.country,
            # Shipping snapshot
            shipping_name=ship.full_name,
            shipping_phone=ship.phone,
            shipping_address=f"{ship.address_line1}, {ship.address_line2 or ''}".strip(", "),
            shipping_city=ship.city,
            shipping_state=ship.state,
            shipping_pincode=ship.pincode,
            shipping_country=ship.country,
        )

        # Create order items + deduct inventory
        for item_data in order_items_data:
            self.session.add(OrderItem(order_id=order.id, **item_data))
            variant = await self.variant_repo.get_by_id(item_data["variant_id"])
            if variant:
                qty_before = variant.stock_quantity
                variant.stock_quantity -= item_data["quantity"]
                self.session.add(variant)
                self.session.add(InventoryLog(
                    variant_id=variant.id,
                    action=InventoryAction.ORDER_RESERVED,
                    quantity_change=-item_data["quantity"],
                    quantity_before=qty_before,
                    quantity_after=variant.stock_quantity,
                    reference_id=order.id,
                    reference_type="order",
                ))

        # Record coupon usage
        if coupon:
            from models.coupon import CouponUsage
            coupon.used_count += 1
            self.session.add(coupon)
            self.session.add(CouponUsage(
                coupon_id=coupon.id,
                user_id=user_id,
                order_id=order.id,
                discount_applied=discount_amount,
            ))

        # Initial status history
        self.session.add(OrderStatusHistory(
            order_id=order.id, status=OrderStatus.PENDING, comment="Order placed"
        ))

        # Clear cart
        for item in cart.items:
            await self.session.delete(item)

        await self.session.flush()
        logger.info("Order created: %s for user_id=%d", order.order_number, user_id)

        # Send confirmation email asynchronously (fire-and-forget)
        from models.user import User
        user = await self.session.get(User, user_id)
        if user:
            await self._send_order_confirmation(user.email, user.first_name, order)

        return order

    async def update_status(self, order_id: int, data: OrderStatusUpdateSchema, admin_id: int) -> Order:
        """Admin: update order status."""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        update_kwargs: dict = {"status": data.status}
        if data.tracking_number:
            update_kwargs["tracking_number"] = data.tracking_number
        if data.courier_name:
            update_kwargs["courier_name"] = data.courier_name
        if data.tracking_url:
            update_kwargs["tracking_url"] = data.tracking_url

        await self.order_repo.update(order, **update_kwargs)
        self.session.add(OrderStatusHistory(
            order_id=order.id,
            status=data.status,
            comment=data.comment,
            updated_by=admin_id,
        ))
        await self.session.flush()
        return order

    async def _apply_coupon(
        self, code: str, user_id: int, subtotal: Decimal
    ) -> tuple:
        from datetime import datetime, timezone
        from models.coupon import CouponType

        coupon = await self.coupon_repo.get_by_code(code)
        if not coupon or not coupon.is_active:
            raise HTTPException(status_code=400, detail="Invalid or inactive coupon")

        now = datetime.now(timezone.utc)
        if now < coupon.valid_from:
            raise HTTPException(status_code=400, detail="Coupon not yet valid")
        if coupon.valid_until and now > coupon.valid_until:
            raise HTTPException(status_code=400, detail="Coupon has expired")
        if subtotal < coupon.min_order_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum order amount ₹{coupon.min_order_amount} required",
            )
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            raise HTTPException(status_code=400, detail="Coupon usage limit reached")

        user_count = await self.coupon_repo.get_user_usage_count(coupon.id, user_id)
        if user_count >= coupon.per_user_limit:
            raise HTTPException(status_code=400, detail="You have already used this coupon")

        if coupon.coupon_type == CouponType.PERCENTAGE:
            discount = subtotal * (coupon.discount_value / 100)
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = coupon.discount_value

        return coupon, discount

    async def _send_order_confirmation(self, email: str, name: str, order: Order) -> None:
        subject = f"Order Confirmed #{order.order_number} — {settings.APP_NAME}"
        body = f"""
        <h2>Hi {name},</h2>
        <p>Your order <strong>{order.order_number}</strong> has been confirmed!</p>
        <p><strong>Total: ₹{order.total_amount}</strong></p>
        <p>We will update you when it ships.</p>
        <p>Thank you for shopping with {settings.APP_NAME}!</p>
        """
        await send_email(email, subject, body)
