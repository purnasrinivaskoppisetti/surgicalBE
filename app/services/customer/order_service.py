import uuid
import logging

from decimal import Decimal

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import SQLAlchemyError

from fastapi import HTTPException

from app.models.models import (
    Order,
    OrderItem,
    CouponUsage,
    Payment,
    Shipment,
    ProductVariant,
    OrderStatus,
    PaymentStatus,
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

from app.services.bluedart_service import (
    BlueDartService
)


logger = logging.getLogger(__name__)


class OrderService:

    # ============================================================
    # HELPER
    # GET VARIANT PRICE
    # ============================================================

    @staticmethod
    def _get_variant_price(
        product,
        variant
    ):

        mrp = (
            variant.mrp
            if variant.mrp is not None
            else product.mrp
        )

        sale_price = (
            variant.sale_price
            if variant.sale_price is not None
            else product.sale_price
        )

        return mrp, sale_price

    # ============================================================
    # HELPER
    # GET AVAILABLE STOCK
    # ============================================================

    @staticmethod
    def _get_available_stock(
        variant
    ):

        return max(
            0,
            variant.stock_qty
            -
            variant.reserved_qty
        )

    # ============================================================
    # CREATE ORDER
    # ============================================================

    @staticmethod
    async def create_order(
        db: AsyncSession,
        user_id,
        payload
    ):

        try:

            # ====================================================
            # GET CART
            # ====================================================

            cart_items = (
                await CartRepository.get_all_cart_items(
                    db=db,
                    user_id=user_id
                )
            )

            if not cart_items:

                return {
                    "success": False,
                    "status_code": 400,
                    "message": "Cart is empty"
                }

            # ====================================================
            # STOCK + PRICE VALIDATION
            # ====================================================

            subtotal = Decimal("0")

            validated_items = []

            for item in cart_items:

                product = item.product

                variant = item.variant

                if not product:

                    raise HTTPException(
                        status_code=400,
                        detail="Product not found for cart item"
                    )

                if not variant:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Variant not found for "
                            f"product '{product.name}'"
                        )
                    )

                if not variant.is_active:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Selected variant for "
                            f"'{product.name}' is no longer available"
                        )
                    )

                # -----------------------------------------------
                # AVAILABLE STOCK
                # -----------------------------------------------

                available_stock = (
                    OrderService._get_available_stock(
                        variant
                    )
                )

                if available_stock < item.quantity:

                    size_color = ""

                    if variant.size:
                        size_color += (
                            f"Size: {variant.size}"
                        )

                    if variant.color:

                        if size_color:
                            size_color += ", "

                        size_color += (
                            f"Color: {variant.color}"
                        )

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Insufficient stock for "
                            f"'{product.name}'"
                            f"{' (' + size_color + ')' if size_color else ''}. "
                            f"Only {available_stock} available."
                        )
                    )

                # -----------------------------------------------
                # PRICE
                # -----------------------------------------------

                mrp, sale_price = (
                    OrderService._get_variant_price(
                        product,
                        variant
                    )
                )

                item_total = (
                    Decimal(str(sale_price))
                    *
                    item.quantity
                )

                subtotal += item_total

                validated_items.append({
                    "cart_item": item,
                    "product": product,
                    "variant": variant,
                    "mrp": mrp,
                    "sale_price": sale_price,
                    "total": item_total
                })

            # ====================================================
            # SHIPPING
            # ====================================================

            settings = (
                await SettingRepository.get_settings(
                    db
                )
            )

            shipping_charge = Decimal("0")

            if settings:

                delivery_charge = Decimal(
                    str(
                        settings.delivery_charge or 0
                    )
                )

                free_shipping_threshold = Decimal(
                    str(
                        settings.free_shipping_threshold or 0
                    )
                )

                if (
                    delivery_charge > 0
                ):

                    if (
                        free_shipping_threshold > 0
                        and
                        subtotal >= free_shipping_threshold
                    ):

                        shipping_charge = Decimal("0")

                    else:

                        shipping_charge = (
                            delivery_charge
                        )

            # ====================================================
            # COUPON
            # ====================================================

            discount = Decimal("0")

            coupon = None

            if payload.coupon_code:

                coupon = (
                    await CouponRepository.get_coupon_by_code(
                        db,
                        payload.coupon_code
                    )
                )

                if not coupon:

                    raise HTTPException(
                        status_code=400,
                        detail="Invalid coupon code"
                    )

                # -----------------------------------------------
                # MINIMUM ORDER
                # -----------------------------------------------

                if (
                    coupon.minimum_order_amount
                    and
                    subtotal
                    <
                    coupon.minimum_order_amount
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Minimum order amount is "
                            f"{coupon.minimum_order_amount}"
                        )
                    )

                # -----------------------------------------------
                # USAGE LIMIT
                # -----------------------------------------------

                if (
                    coupon.usage_limit
                    and
                    coupon.used_count
                    >=
                    coupon.usage_limit
                ):

                    raise HTTPException(
                        status_code=400,
                        detail="Coupon usage limit reached"
                    )

                # -----------------------------------------------
                # FLAT
                # -----------------------------------------------

                if (
                    coupon.coupon_type.value
                    ==
                    "flat"
                ):

                    discount = (
                        coupon.discount_value
                    )

                # -----------------------------------------------
                # PERCENTAGE
                # -----------------------------------------------

                elif (
                    coupon.coupon_type.value
                    ==
                    "percentage"
                ):

                    discount = (
                        subtotal
                        *
                        coupon.discount_value
                    ) / Decimal("100")

                    if (
                        coupon.max_discount_amount
                        and
                        discount
                        >
                        coupon.max_discount_amount
                    ):

                        discount = (
                            coupon.max_discount_amount
                        )

                # -----------------------------------------------
                # FREE SHIPPING
                # -----------------------------------------------

                elif (
                    coupon.coupon_type.value
                    ==
                    "free_shipping"
                ):

                    discount = (
                        shipping_charge
                    )

            # ====================================================
            # PREVENT NEGATIVE TOTAL
            # ====================================================

            total_amount = max(
                Decimal("0"),
                subtotal
                +
                shipping_charge
                -
                discount
            )

            # ====================================================
            # CREATE ORDER
            # ====================================================

            order = Order(

                order_number=(
                    f"SW-"
                    f"{uuid.uuid4().hex[:10].upper()}"
                ),

                user_id=user_id,

                address_id=payload.address_id,

                coupon_id=(
                    coupon.id
                    if coupon
                    else None
                ),

                coupon_code=(
                    coupon.code
                    if coupon
                    else None
                ),

                subtotal=subtotal,

                gst_amount=Decimal("0"),

                shipping_charge=shipping_charge,

                discount=discount,

                total_amount=total_amount,

                status=OrderStatus.PENDING,

                payment_status=PaymentStatus.PENDING

            )

            await OrderRepository.create_order(
                db,
                order
            )

            # ====================================================
            # CREATE ORDER ITEMS
            # ====================================================

            for data in validated_items:

                product = data["product"]

                variant = data["variant"]

                sale_price = data["sale_price"]

                item = data["cart_item"]

                item_total = data["total"]

                order_item = OrderItem(

                    order_id=order.id,

                    product_id=product.id,

                    variant_id=variant.id,

                    product_name=product.name,

                    product_sku=variant.sku,

                    size=variant.size,

                    color=variant.color,

                    variant_attributes=(
                        variant.attributes
                    ),

                    quantity=item.quantity,

                    price=sale_price,

                    gst_amount=Decimal("0"),

                    total=item_total

                )

                await OrderRepository.create_order_item(
                    db,
                    order_item
                )

            # ====================================================
            # CREATE PAYMENT
            # ====================================================

            payment = Payment(

                order_id=order.id,

                payment_method=(
                    payload.payment_method
                ),

                amount=total_amount,

                status=PaymentStatus.PENDING

            )

            db.add(payment)

            await db.commit()

            await db.refresh(order)

            # ====================================================
            # RESPONSE
            # ====================================================

            return {

                "success": True,

                "status_code": 201,

                "message": (
                    "Order created. Complete payment."
                ),

                "data": {

                    "order_id": str(
                        order.id
                    ),

                    "order_number": (
                        order.order_number
                    ),

                    "amount": float(
                        total_amount
                    )

                }

            }

        except HTTPException:

            await db.rollback()

            raise

        except SQLAlchemyError as e:

            await db.rollback()

            logger.exception(
                "Database error while creating order"
            )

            raise HTTPException(
                status_code=500,
                detail="Database error while creating order"
            )

        except Exception as e:

            await db.rollback()

            logger.exception(
                "Error while creating order"
            )

            raise HTTPException(
                status_code=500,
                detail="Something went wrong while creating order"
            )

    # ============================================================
    # PAYMENT SUCCESS
    # ============================================================

    @staticmethod
    async def payment_success(
        db: AsyncSession,
        user_id,
        payload
    ):

        try:

            # ====================================================
            # GET ORDER
            # ====================================================

            order = (
                await OrderRepository.get_customer_order(
                    db=db,
                    order_id=payload.order_id,
                    user_id=user_id
                )
            )

            if not order:

                return {
                    "success": False,
                    "status_code": 404,
                    "message": "Order not found"
                }

            # ====================================================
            # IDEMPOTENCY
            # ====================================================

            if (
                order.payment_status
                ==
                PaymentStatus.PAID
            ):

                return {
                    "success": False,
                    "status_code": 400,
                    "message": "Payment already completed"
                }

            # ====================================================
            # LOCK + VALIDATE VARIANT STOCK
            # ====================================================

            locked_variants = {}

            for item in order.items:

                if not item.variant_id:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Variant missing for "
                            f"order item '{item.product_name}'"
                        )
                    )

                result = await db.execute(

                    select(ProductVariant)

                    .where(
                        ProductVariant.id
                        ==
                        item.variant_id
                    )

                    .with_for_update()

                )

                variant = (
                    result.scalar_one_or_none()
                )

                if not variant:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Variant not found for "
                            f"'{item.product_name}'"
                        )
                    )

                available_stock = (
                    OrderService._get_available_stock(
                        variant
                    )
                )

                if (
                    available_stock
                    <
                    item.quantity
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Insufficient stock for "
                            f"'{item.product_name}'. "
                            f"Only {available_stock} available."
                        )
                    )

                locked_variants[
                    item.variant_id
                ] = variant

            # ====================================================
            # UPDATE PAYMENT
            # ====================================================

            if order.payments:

                payment = order.payments[0]

                payment.status = (
                    PaymentStatus.PAID
                )

                payment.gateway_transaction_id = (
                    payload.transaction_id
                )

            # ====================================================
            # UPDATE ORDER
            # ====================================================

            order.payment_status = (
                PaymentStatus.PAID
            )

            order.status = (
                OrderStatus.CONFIRMED
            )

            # ====================================================
            # DECREASE VARIANT STOCK
            # ====================================================

            for item in order.items:

                variant = locked_variants[
                    item.variant_id
                ]

                variant.stock_qty -= (
                    item.quantity
                )

            # ====================================================
            # COUPON USAGE
            # ====================================================

            if order.coupon_id:

                coupon_usage = CouponUsage(

                    coupon_id=order.coupon_id,

                    user_id=user_id,

                    order_id=order.id,

                    discount_amount=(
                        order.discount
                    )

                )

                db.add(
                    coupon_usage
                )

                if order.coupon:

                    order.coupon.used_count += 1

            # ====================================================
            # CLEAR CART
            # ====================================================

            cart_items = (
                await CartRepository.get_all_cart_items(
                    db,
                    user_id
                )
            )

            for cart_item in cart_items:

                await db.delete(
                    cart_item
                )

            # ====================================================
            # COMMIT PAYMENT + STOCK
            # ====================================================

            await db.commit()

            await db.refresh(order)

            # ====================================================
            # BLUE DART WAYBILL
            # ====================================================

            waybill_info = None

            try:

                if order.address:

                    waybill_res = (
                        await BlueDartService.generate_waybill(
                            order,
                            order.address
                        )
                    )

                    shipment = Shipment(

                        id=uuid.uuid4(),

                        order_id=order.id,

                        courier_name="Blue Dart",

                        tracking_number=(
                            waybill_res.get(
                                "awb_number"
                            )
                        ),

                        pickup_token_number=(
                            waybill_res.get(
                                "pickup_token_number"
                            )
                        ),

                        origin_area=(
                            waybill_res.get(
                                "origin_area"
                            )
                        ),

                        destination_area=(
                            waybill_res.get(
                                "destination_area"
                            )
                        ),

                        destination_location=(
                            waybill_res.get(
                                "destination_location"
                            )
                        ),

                        status="MANIFESTED"

                    )

                    db.add(
                        shipment
                    )

                    order.status = (
                        OrderStatus.PACKED
                    )

                    await db.commit()

                    waybill_info = {

                        "awb_number": (
                            waybill_res.get(
                                "awb_number"
                            )
                        ),

                        "pickup_token_number": (
                            waybill_res.get(
                                "pickup_token_number"
                            )
                        )

                    }

            except Exception as e:

                logger.exception(
                    "Blue Dart waybill generation failed "
                    f"for order {order.order_number}: {e}"
                )

                # Payment remains successful.
                # Admin can retry shipment generation.

            # ====================================================
            # RESPONSE
            # ====================================================

            return {

                "success": True,

                "status_code": 200,

                "message": (
                    "Payment successful. "
                    "Order confirmed."
                ),

                "data": {

                    "order_id": str(
                        order.id
                    ),

                    "order_number": (
                        order.order_number
                    ),

                    "payment_status": (
                        order.payment_status.value
                    ),

                    "order_status": (
                        order.status.value
                    ),

                    "waybill": waybill_info

                }

            }

        except HTTPException:

            await db.rollback()

            raise

        except SQLAlchemyError:

            await db.rollback()

            logger.exception(
                "Database error during payment success"
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Database error while processing payment"
                )
            )

        except Exception:

            await db.rollback()

            logger.exception(
                "Unexpected payment success error"
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Something went wrong while processing payment"
                )
            )

    # ============================================================
    # GET ALL ORDERS
    # ============================================================

    @staticmethod
    async def get_orders(
        db: AsyncSession,
        user_id
    ):

        orders = (
            await OrderRepository.get_orders_by_user(
                db,
                user_id
            )
        )

        data = []

        for order in orders:

            latest_shipment = (

                order.shipments[0]

                if order.shipments

                else None

            )

            products = []

            for item in order.items:

                products.append({

                    "product_id": str(
                        item.product_id
                    ),

                    "variant_id": (
                        str(item.variant_id)
                        if item.variant_id
                        else None
                    ),

                    "product_name": (
                        item.product_name
                    ),

                    "product_sku": (
                        item.product_sku
                    ),

                    "size": item.size,

                    "color": item.color,

                    "quantity": (
                        item.quantity
                    ),

                    "price": float(
                        item.price or 0
                    ),

                    "total": float(
                        item.total or 0
                    ),

                    "product_image": (

                        item.product.thumbnail_url

                        if item.product

                        else None

                    )

                })

            data.append({

                "order_id": str(
                    order.id
                ),

                "order_number": (
                    order.order_number
                ),

                "status": (

                    order.status.value

                    if hasattr(
                        order.status,
                        "value"
                    )

                    else str(
                        order.status
                    )

                ),

                "payment_status": (

                    order.payment_status.value

                    if hasattr(
                        order.payment_status,
                        "value"
                    )

                    else str(
                        order.payment_status
                    )

                ),

                "total_amount": float(
                    order.total_amount or 0
                ),

                "order_date": (
                    order.created_at
                ),

                "tracking_number": (

                    latest_shipment.tracking_number

                    if latest_shipment

                    else None

                ),

                "delivery_status": (

                    latest_shipment.status

                    if latest_shipment

                    else None

                ),

                "products": products

            })

        return {

            "success": True,

            "status_code": 200,

            "message": (
                "Orders fetched successfully"
            ),

            "data": data

        }

    # ============================================================
    # GET SINGLE ORDER
    # ============================================================

    @staticmethod
    async def get_order(
        db: AsyncSession,
        user_id,
        order_id
    ):

        order = (
            await OrderRepository.get_customer_order(
                db=db,
                order_id=order_id,
                user_id=user_id
            )
        )

        if not order:

            return {

                "success": False,

                "status_code": 404,

                "message": "Order not found"

            }

        shipments_list = []

        for shipment in (
            getattr(
                order,
                "shipments",
                []
            )
        ):

            shipments_list.append({

                "shipment_id": str(
                    shipment.id
                ),

                "courier_name": (
                    shipment.courier_name
                ),

                "tracking_number": (
                    shipment.tracking_number
                ),

                "pickup_token_number": (
                    shipment.pickup_token_number
                ),

                "status": shipment.status,

                "last_scanned_location": (
                    shipment.last_scanned_location
                ),

                "last_scanned_at": (

                    shipment.last_scanned_at.isoformat()

                    if shipment.last_scanned_at

                    else None

                ),

                "estimated_delivery": (

                    shipment.estimated_delivery.isoformat()

                    if shipment.estimated_delivery

                    else None

                ),

                "awb_pdf_url": (
                    shipment.awb_pdf_url
                )

            })

        return {

            "success": True,

            "status_code": 200,

            "message": (
                "Order details fetched successfully"
            ),

            "data": {

                "order_id": str(
                    order.id
                ),

                "order_number": (
                    order.order_number
                ),

                "order_date": (
                    order.created_at
                ),

                "status": (
                    order.status.value
                ),

                "payment_status": (
                    order.payment_status.value
                ),

                "subtotal": float(
                    order.subtotal
                ),

                "shipping_charge": float(
                    order.shipping_charge
                ),

                "discount": float(
                    order.discount
                ),

                "total_amount": float(
                    order.total_amount
                ),

                "shipments": shipments_list,

                "items": [

                    {

                        "product_id": str(
                            item.product_id
                        ),

                        "variant_id": (

                            str(
                                item.variant_id
                            )

                            if item.variant_id

                            else None

                        ),

                        "product_name": (
                            item.product_name
                        ),

                        "product_sku": (
                            item.product_sku
                        ),

                        "size": (
                            item.size
                        ),

                        "color": (
                            item.color
                        ),

                        "variant_attributes": (
                            item.variant_attributes
                        ),

                        "product_image": (

                            item.product.thumbnail_url

                            if item.product

                            else None

                        ),

                        "quantity": (
                            item.quantity
                        ),

                        "price": float(
                            item.price
                        ),

                        "total": float(
                            item.total
                        )

                    }

                    for item
                    in order.items

                ]

            }

        }

    # ============================================================
    # CANCEL ORDER
    # ============================================================

    @staticmethod
    async def cancel_order(
        db: AsyncSession,
        user_id,
        order_id,
        reason
    ):

        try:

            order = (
                await OrderRepository.get_customer_order(
                    db=db,
                    order_id=order_id,
                    user_id=user_id
                )
            )

            if not order:

                return {

                    "success": False,

                    "status_code": 404,

                    "message": "Order not found"

                }

            # ----------------------------------------------------
            # ALREADY CANCELLED
            # ----------------------------------------------------

            if (
                order.status
                ==
                OrderStatus.CANCELLED
            ):

                return {

                    "success": False,

                    "status_code": 400,

                    "message": "Order is already cancelled"

                }

            # ----------------------------------------------------
            # CANNOT CANCEL
            # ----------------------------------------------------

            if order.status in [

                OrderStatus.SHIPPED,

                OrderStatus.OUT_FOR_DELIVERY,

                OrderStatus.DELIVERED

            ]:

                return {

                    "success": False,

                    "status_code": 400,

                    "message": (
                        "Order cannot be cancelled "
                        "after dispatch"
                    )

                }

            # ----------------------------------------------------
            # RESTOCK ONLY IF PAYMENT WAS PAID
            # ----------------------------------------------------

            if (
                order.payment_status
                ==
                PaymentStatus.PAID
            ):

                for item in order.items:

                    if not item.variant_id:

                        continue

                    result = await db.execute(

                        select(ProductVariant)

                        .where(
                            ProductVariant.id
                            ==
                            item.variant_id
                        )

                        .with_for_update()

                    )

                    variant = (
                        result.scalar_one_or_none()
                    )

                    if variant:

                        variant.stock_qty += (
                            item.quantity
                        )

            # ----------------------------------------------------
            # CANCEL ORDER
            # ----------------------------------------------------

            order.status = (
                OrderStatus.CANCELLED
            )

            order.cancel_reason = (
                reason
            )

            await db.commit()

            return {

                "success": True,

                "status_code": 200,

                "message": (
                    "Order cancelled successfully"
                )

            }

        except HTTPException:

            await db.rollback()

            raise

        except SQLAlchemyError:

            await db.rollback()

            raise HTTPException(

                status_code=500,

                detail=(
                    "Database error while cancelling order"
                )

            )

        except Exception:

            await db.rollback()

            logger.exception(
                "Order cancellation failed"
            )

            raise HTTPException(

                status_code=500,

                detail=(
                    "Something went wrong while cancelling order"
                )

            )