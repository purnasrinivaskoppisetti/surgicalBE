import uuid

from decimal import Decimal

from app.models.models import (
    Order,
    OrderItem,
    CouponUsage,
    OrderStatus,
    PaymentStatus
)

from app.repositories.cart_repository import (
    CartRepository
)

from app.repositories.order_repository import (
    OrderRepository
)

from app.repositories.coupon_repository import (
    CouponRepository
)

from app.repositories.setting_repository import (
    SettingRepository
)


class OrderService:

    @staticmethod
    async def create_order(
        db,
        user_id,
        payload
    ):

        cart_items = await (
            CartRepository.get_all_cart_items(
                db,
                user_id
            )
        )

        if not cart_items:

            return {
                "success": False,
                "status_code": 400,
                "message": "Cart is empty"
            }

        subtotal = Decimal("0")

        for item in cart_items:

            subtotal += (
                item.product.sale_price *
                item.quantity
            )

        settings = await (
            SettingRepository.get_settings(
                db
            )
        )

        shipping_charge = Decimal("0")

        if settings:

            if (
                subtotal <
                settings.free_shipping_threshold
            ):
                shipping_charge = (
                    settings.delivery_charge
                )

        discount = Decimal("0")

        coupon = None

        if payload.coupon_code:

            coupon = await (
                CouponRepository.get_by_code(
                    db,
                    payload.coupon_code
                )
            )

            if coupon:

                if (
                    coupon.coupon_type.value
                    == "flat"
                ):
                    discount = (
                        coupon.discount_value
                    )

                elif (
                    coupon.coupon_type.value
                    == "percentage"
                ):
                    discount = (
                        subtotal *
                        coupon.discount_value
                    ) / Decimal("100")

        total_amount = (
            subtotal +
            shipping_charge -
            discount
        )

        order = Order(
            order_number=
            f"SW-{uuid.uuid4().hex[:10].upper()}",
            user_id=user_id,
            address_id=payload.address_id,
            coupon_id=
            coupon.id if coupon else None,
            coupon_code=
            coupon.code if coupon else None,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            subtotal=subtotal,
            gst_amount=0,
            shipping_charge=shipping_charge,
            discount=discount,
            total_amount=total_amount
        )

        await OrderRepository.create_order(
            db,
            order
        )

        for cart_item in cart_items:

            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product.id,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                quantity=cart_item.quantity,
                price=cart_item.product.sale_price,
                gst_amount=0,
                total=
                cart_item.product.sale_price *
                cart_item.quantity
            )

            await (
                OrderRepository
                .create_order_item(
                    db,
                    order_item
                )
            )

            cart_item.product.stock_qty -= (
                cart_item.quantity
            )

        if coupon:

            coupon_usage = CouponUsage(
                coupon_id=coupon.id,
                user_id=user_id,
                order_id=order.id,
                discount_amount=discount
            )

            db.add(coupon_usage)

            coupon.used_count += 1

        for item in cart_items:

            await db.delete(item)

        await db.commit()

        return {
            "success": True,
            "status_code": 201,
            "message": "Order placed successfully",
            "data": {
                "order_id": str(order.id),
                "order_number":
                order.order_number,
                "subtotal":
                float(subtotal),
                "shipping_charge":
                float(shipping_charge),
                "discount":
                float(discount),
                "total_amount":
                float(total_amount)
            }
        }