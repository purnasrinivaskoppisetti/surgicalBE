import logging

from datetime import datetime, timezone

from fastapi import HTTPException

from razorpay.errors import (
    SignatureVerificationError,
)

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.razorpay import client

from app.models.models import (
    PaymentStatus,
    OrderStatus,
    ProductVariant,
    StoreSetting,
    Shipment,
)

from app.repositories.bill_repository import (
    BillRepository,
)

from app.repositories.cart_repository import (
    CartRepository,
)

from app.repositories.shipment_repository import (
    ShipmentRepository,
)

from app.services.bluedart_service import (
    BlueDartService,
)


logger = logging.getLogger(__name__)


class BillingService:

    # ============================================================
    # CREATE RAZORPAY PAYMENT
    # ============================================================

    @staticmethod
    async def create_payment(
        db: AsyncSession,
        user_id,
        order_id,
    ):

        # --------------------------------------------------------
        # GET ORDER
        # --------------------------------------------------------

        order = await BillRepository.get_order(
            db=db,
            order_id=order_id,
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # VERIFY ORDER OWNER
        # --------------------------------------------------------

        if str(order.user_id) != str(user_id):

            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # --------------------------------------------------------
        # VERIFY ORDER STATUS
        # --------------------------------------------------------

        if (
            order.payment_status
            == PaymentStatus.PAID
        ):

            raise HTTPException(
                status_code=400,
                detail="Order payment is already completed",
            )

        # --------------------------------------------------------
        # GET PAYMENT
        # --------------------------------------------------------

        payment = (
            await BillRepository.get_payment_by_order(
                db=db,
                order_id=order.id,
            )
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment record not found",
            )

        # --------------------------------------------------------
        # PAYMENT ALREADY PAID
        # --------------------------------------------------------

        if (
            payment.status
            == PaymentStatus.PAID
        ):

            raise HTTPException(
                status_code=400,
                detail="Payment is already completed",
            )

        # --------------------------------------------------------
        # AMOUNT
        # --------------------------------------------------------

        amount_in_paise = int(
            round(
                float(
                    order.total_amount
                ) * 100
            )
        )

        if amount_in_paise <= 0:

            raise HTTPException(
                status_code=400,
                detail="Invalid order amount",
            )

        # --------------------------------------------------------
        # CREATE RAZORPAY ORDER
        # --------------------------------------------------------

        try:

            razorpay_order = client.order.create({

                "amount":
                    amount_in_paise,

                "currency":
                    "INR",

                "receipt":
                    str(
                        order.order_number
                    ),

            })

        except Exception as exc:

            logger.exception(
                "Failed to create Razorpay order"
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to create Razorpay order"
                ),
            )

        # --------------------------------------------------------
        # SAVE RAZORPAY ORDER ID
        # --------------------------------------------------------

        payment.gateway_order_id = (
            razorpay_order["id"]
        )

        payment.amount = (
            order.total_amount
        )

        await db.commit()

        return {

            "success": True,

            "status_code": 200,

            "message":
                "Payment order created successfully",

            "data": {

                "order_id":
                    str(order.id),

                "order_number":
                    order.order_number,

                "razorpay_order_id":
                    razorpay_order["id"],

                "amount":
                    razorpay_order["amount"],

                "currency":
                    razorpay_order["currency"],

                "razorpay_key":
                    client.auth[0]
                    if False
                    else None,

            },
        }


    # ============================================================
    # VERIFY RAZORPAY PAYMENT
    #
    # THIS IS THE ONLY PLACE WHERE PAYMENT BECOMES PAID.
    # ============================================================

    @staticmethod
    async def verify_payment(
        db: AsyncSession,
        user_id,
        payload,
    ):

        # ========================================================
        # 1. GET ORDER
        # ========================================================

        order = await BillRepository.get_order(
            db=db,
            order_id=payload.order_id,
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # SAVE PLAIN ID
        # --------------------------------------------------------

        order_id = order.id

        order_id_str = str(
            order_id
        )

        # ========================================================
        # 2. VERIFY OWNER
        # ========================================================

        if str(order.user_id) != str(user_id):

            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # ========================================================
        # 3. VERIFY RAZORPAY SIGNATURE
        # ========================================================

        try:

            client.utility.verify_payment_signature({

                "razorpay_order_id":
                    payload.razorpay_order_id,

                "razorpay_payment_id":
                    payload.razorpay_payment_id,

                "razorpay_signature":
                    payload.razorpay_signature,

            })

        except SignatureVerificationError:

            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature",
            )

        except Exception:

            logger.exception(
                "Razorpay signature verification failed"
            )

            raise HTTPException(
                status_code=400,
                detail="Unable to verify payment",
            )

        # ========================================================
        # 4. GET PAYMENT WITH LOCK
        # ========================================================

        payment = (
            await BillRepository.get_payment_for_update(
                db=db,
                order_id=order_id,
            )
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment record not found",
            )

        # ========================================================
        # 5. VERIFY RAZORPAY ORDER ID
        # ========================================================

        if (
            payment.gateway_order_id
            !=
            payload.razorpay_order_id
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay order ID does not match "
                    "the payment record"
                ),
            )

        # ========================================================
        # 6. IDEMPOTENCY
        # ========================================================

        if (
            payment.status
            == PaymentStatus.PAID
        ):

            await db.rollback()

            return {

                "success":
                    True,

                "status_code":
                    200,

                "message":
                    "Payment already verified",

                "data": {

                    "order_id":
                        order_id_str,

                    "payment_status":
                        "PAID",

                },
            }

        # ========================================================
        # 7. LOCK ALL VARIANTS
        # ========================================================

        locked_variants = {}

        try:

            for item in order.items:

                if not item.variant_id:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Variant missing for "
                            f"order item "
                            f"'{item.product_name}'"
                        ),
                    )

                result = await db.execute(

                    select(
                        ProductVariant
                    )

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
                        ),
                    )

                # ------------------------------------------------
                # ACTIVE CHECK
                # ------------------------------------------------

                if not variant.is_active:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Variant for "
                            f"'{item.product_name}' "
                            f"is no longer available"
                        ),
                    )

                # ------------------------------------------------
                # AVAILABLE STOCK
                # ------------------------------------------------

                reserved_qty = (
                    variant.reserved_qty or 0
                )

                stock_qty = (
                    variant.stock_qty or 0
                )

                available_stock = (
                    stock_qty
                    -
                    reserved_qty
                )

                if (
                    available_stock
                    <
                    item.quantity
                ):

                    size_color = []

                    if variant.size:

                        size_color.append(
                            f"Size: {variant.size}"
                        )

                    if variant.color:

                        size_color.append(
                            f"Color: {variant.color}"
                        )

                    variant_text = ""

                    if size_color:

                        variant_text = (
                            " ("
                            +
                            ", ".join(
                                size_color
                            )
                            +
                            ")"
                        )

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Insufficient stock for "
                            f"'{item.product_name}'"
                            f"{variant_text}. "
                            f"Only "
                            f"{available_stock} "
                            f"available."
                        ),
                    )

                locked_variants[
                    item.variant_id
                ] = variant

            # ====================================================
            # 8. DECREASE VARIANT STOCK
            # ====================================================

            for item in order.items:

                variant = (
                    locked_variants[
                        item.variant_id
                    ]
                )

                variant.stock_qty = (
                    variant.stock_qty
                    -
                    item.quantity
                )

            # ====================================================
            # 9. UPDATE PAYMENT
            # ====================================================

            payment.status = (
                PaymentStatus.PAID
            )

            payment.gateway_order_id = (
                payload.razorpay_order_id
            )

            payment.gateway_transaction_id = (
                payload.razorpay_payment_id
            )

            payment.payment_response_data = {

                "razorpay_order_id":
                    payload.razorpay_order_id,

                "razorpay_payment_id":
                    payload.razorpay_payment_id,

                "razorpay_signature":
                    payload.razorpay_signature,

            }

            payment.paid_at = (
                datetime.now(
                    timezone.utc
                )
            )

            # ====================================================
            # 10. UPDATE ORDER
            # ====================================================

            order.payment_status = (
                PaymentStatus.PAID
            )

            order.status = (
                OrderStatus.CONFIRMED
            )

            # ====================================================
            # 11. CLEAR CART
            # ====================================================

            cart_items = (
                await CartRepository.get_all_cart_items(
                    db=db,
                    user_id=user_id,
                )
            )

            for cart_item in cart_items:

                await db.delete(
                    cart_item
                )

            # ====================================================
            # 12. COMMIT PAYMENT + STOCK + CART
            # ====================================================

            await db.commit()

        except HTTPException:

            await db.rollback()

            raise

        except Exception:

            await db.rollback()

            logger.exception(
                "Payment processing failed"
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Payment processing failed"
                ),
            )

        # ========================================================
        # 13. RELOAD ORDER
        # ========================================================

        order = await BillRepository.get_order(
            db=db,
            order_id=order_id,
        )

        if not order:

            return {

                "success":
                    True,

                "status_code":
                    200,

                "message":
                    "Payment successful",

                "data": {

                    "order_id":
                        order_id_str,

                    "payment_status":
                        "PAID",

                },
            }

        # ========================================================
        # 14. CHECK ADDRESS
        # ========================================================

        if not order.address:

            return {

                "success":
                    True,

                "status_code":
                    200,

                "message": (
                    "Payment successful, "
                    "but delivery address is missing"
                ),

                "data": {

                    "order_id":
                        order_id_str,

                    "payment_status":
                        "PAID",

                    "order_status":
                        "CONFIRMED",

                    "waybill_generated":
                        False,

                    "waybill_error":
                        "Delivery address is missing",

                },
            }

        # ========================================================
        # 15. CHECK EXISTING SHIPMENT
        # ========================================================

        existing_shipment = (
            await ShipmentRepository.get_by_order_id(
                db=db,
                order_id=order_id,
            )
        )

        if (
            existing_shipment
            and
            existing_shipment.tracking_number
        ):

            return {

                "success":
                    True,

                "status_code":
                    200,

                "message": (
                    "Payment successful. "
                    "Waybill already exists."
                ),

                "data": {

                    "order_id":
                        order_id_str,

                    "payment_status":
                        "PAID",

                    "order_status": (
                        order.status.value
                        if hasattr(
                            order.status,
                            "value",
                        )
                        else str(
                            order.status
                        )
                    ),

                    "waybill_generated":
                        True,

                    "awb_number":
                        existing_shipment.tracking_number,

                    "courier":
                        existing_shipment.courier_name,

                },
            }

        # ========================================================
        # 16. GENERATE BLUE DART WAYBILL
        # ========================================================

        try:

            # ----------------------------------------------------
            # STORE SETTINGS
            # ----------------------------------------------------

            store_result = await db.execute(

                select(
                    StoreSetting
                )

                .limit(1)

            )

            store_setting = (
                store_result
                .scalar_one_or_none()
            )

            # ----------------------------------------------------
            # BLUE DART
            # ----------------------------------------------------

            waybill_data = (
                await BlueDartService.generate_waybill(

                    order=order,

                    address=order.address,

                    store_setting=store_setting,

                )
            )

            # ----------------------------------------------------
            # AWB
            # ----------------------------------------------------

            awb_number = (
                waybill_data.get(
                    "awb_number"
                )
            )

            if not awb_number:

                raise Exception(
                    "Blue Dart did not return AWB number"
                )

            # ====================================================
            # 17. CREATE SHIPMENT
            # ====================================================

            shipment = Shipment(

                order_id=order_id,

                tracking_number=(
                    awb_number
                ),

                courier_name=(
                    "Blue Dart"
                ),

                pickup_token_number=(
                    waybill_data.get(
                        "pickup_token_number"
                    )
                ),

                cluster_code=(
                    waybill_data.get(
                        "cluster_code"
                    )
                ),

                destination_area=(
                    waybill_data.get(
                        "destination_area"
                    )
                ),

                destination_location=(
                    waybill_data.get(
                        "destination_location"
                    )
                ),

                mps_details=(
                    waybill_data.get(
                        "mps_details"
                    )
                ),

            )

            # ====================================================
            # 18. SAVE SHIPMENT
            # ====================================================

            shipment = (
                await ShipmentRepository.create_shipment(

                    db=db,

                    shipment=shipment,

                )
            )

            # ====================================================
            # OPTIONAL SHIPPING FIELDS
            # ====================================================

            optional_fields = {

                "actual_weight":
                    "actual_weight",

                "length":
                    "length",

                "breadth":
                    "breadth",

                "height":
                    "height",

                "piece_count":
                    "piece_count",

                "product_code":
                    "product_code",

                "sub_product_code":
                    "sub_product_code",

                "pack_type":
                    "pack_type",

            }

            for (
                model_field,
                response_field,
            ) in optional_fields.items():

                if hasattr(
                    shipment,
                    model_field,
                ):

                    setattr(

                        shipment,

                        model_field,

                        waybill_data.get(
                            response_field
                        ),

                    )

            # ====================================================
            # 19. ORDER PACKED
            # ====================================================

            order.status = (
                OrderStatus.PACKED
            )

            await db.commit()

            await db.refresh(
                order
            )

            await db.refresh(
                shipment
            )

            # ====================================================
            # 20. RESPONSE
            # ====================================================

            return {

                "success":
                    True,

                "status_code":
                    200,

                "message": (
                    "Payment successful and "
                    "Blue Dart Waybill generated successfully."
                ),

                "data": {

                    "order_id":
                        order_id_str,

                    "payment_status":
                        "PAID",

                    "order_status": (
                        order.status.value
                        if hasattr(
                            order.status,
                            "value",
                        )
                        else str(
                            order.status
                        )
                    ),

                    "waybill_generated":
                        True,

                    "courier":
                        "Blue Dart",

                    "awb_number":
                        awb_number,

                    "pickup_token_number":
                        waybill_data.get(
                            "pickup_token_number"
                        ),

                    "cluster_code":
                        waybill_data.get(
                            "cluster_code"
                        ),

                    "destination_area":
                        waybill_data.get(
                            "destination_area"
                        ),

                    "destination_location":
                        waybill_data.get(
                            "destination_location"
                        ),

                },

            }

        except Exception as exc:

            # ----------------------------------------------------
            # IMPORTANT
            #
            # Payment is already committed.
            #
            # We DO NOT rollback payment/stock.
            #
            # Only shipment generation failed.
            # ----------------------------------------------------

            await db.rollback()

            logger.exception(
                "Blue Dart waybill generation failed "
                "for order %s",
                order_id_str,
            )

            return {

                "success":
                    True,

                "status_code":
                    200,

                "message": (
                    "Payment successful, "
                    "but Blue Dart Waybill generation "
                    "is pending."
                ),

                "data": {

                    "order_id":
                        order_id_str,

                    "payment_status":
                        "PAID",

                    "order_status":
                        "CONFIRMED",

                    "waybill_generated":
                        False,

                    "waybill_error":
                        str(exc),

                },

            }