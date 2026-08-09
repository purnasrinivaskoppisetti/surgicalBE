# app/services/shop/billing_service.py

from datetime import datetime

from fastapi import HTTPException
from razorpay.errors import SignatureVerificationError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.razorpay import client

from app.models.models import (
    PaymentStatus,
    OrderStatus,
    StoreSetting,
)

from app.repositories.bill_repository import (
    BillRepository,
)

from app.repositories.order_repository import (
    OrderRepository,
)

from app.repositories.shipment_repository import (
    ShipmentRepository,
)

from app.services.bluedart_service import (
    BlueDartService,
)


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

        order = await BillRepository.get_order(
            db,
            order_id,
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # VERIFY OWNER
        # --------------------------------------------------------

        if str(order.user_id) != str(user_id):

            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # --------------------------------------------------------
        # GET PAYMENT
        # --------------------------------------------------------

        payment = (
            await BillRepository
            .get_payment_by_order(
                db,
                order.id,
            )
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        # --------------------------------------------------------
        # ALREADY PAID
        # --------------------------------------------------------

        if payment.status == PaymentStatus.PAID:

            raise HTTPException(
                status_code=400,
                detail="Order payment is already completed",
            )

        # --------------------------------------------------------
        # CREATE RAZORPAY ORDER
        # --------------------------------------------------------

        try:

            razorpay_order = client.order.create(
                {
                    "amount": int(
                        float(order.total_amount) * 100
                    ),

                    "currency": "INR",

                    "receipt": str(
                        order.order_number
                    ),
                }
            )

        except Exception as exc:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to create Razorpay order: "
                    f"{str(exc)}"
                ),
            )

        # --------------------------------------------------------
        # SAVE RAZORPAY ORDER ID
        # --------------------------------------------------------

        payment.gateway_order_id = (
            razorpay_order["id"]
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

                "razorpay_order_id":
                    razorpay_order["id"],

                "amount":
                    razorpay_order["amount"],

                "currency":
                    razorpay_order["currency"],
            },
        }

    # ============================================================
    # VERIFY PAYMENT + AUTO WAYBILL
    # ============================================================

    @staticmethod
    async def verify_payment(
        db: AsyncSession,
        user_id,
        payload,
    ):

        # ========================================================
        # 1. VERIFY RAZORPAY SIGNATURE
        # ========================================================

        try:

            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id":
                        payload.razorpay_order_id,

                    "razorpay_payment_id":
                        payload.razorpay_payment_id,

                    "razorpay_signature":
                        payload.razorpay_signature,
                }
            )

        except SignatureVerificationError:

            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature",
            )

        # ========================================================
        # 2. GET ORDER
        # ========================================================

        order = await BillRepository.get_order(
            db,
            payload.order_id,
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # ========================================================
        # 3. VERIFY OWNERSHIP
        # ========================================================

        if str(order.user_id) != str(user_id):

            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # ========================================================
        # 4. GET PAYMENT
        # ========================================================

        payment = (
            await BillRepository
            .get_payment_by_order(
                db,
                payload.order_id,
            )
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        # ========================================================
        # 5. UPDATE PAYMENT
        # ========================================================

        if payment.status != PaymentStatus.PAID:

            payment.status = (
                PaymentStatus.PAID
            )

            payment.gateway_transaction_id = (
                payload.razorpay_payment_id
            )

            payment.gateway_order_id = (
                payload.razorpay_order_id
            )

            payment.payment_response_data = {

                "razorpay_payment_id":
                    payload.razorpay_payment_id,

                "razorpay_order_id":
                    payload.razorpay_order_id,

                "razorpay_signature":
                    payload.razorpay_signature,
            }

            payment.paid_at = (
                datetime.utcnow()
            )

        # ========================================================
        # 6. UPDATE ORDER
        # ========================================================

        order.payment_status = (
            PaymentStatus.PAID
        )

        # Only move to CONFIRMED if not already further ahead

        if order.status not in (
            OrderStatus.PACKED,
            OrderStatus.SHIPPED,
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.DELIVERED,
        ):

            order.status = (
                OrderStatus.CONFIRMED
            )

        # ========================================================
        # 7. COMMIT PAYMENT FIRST
        # ========================================================

        await db.commit()

        # ========================================================
        # 8. RELOAD COMPLETE ORDER
        # ========================================================

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order.id,
            )
        )

        if not order:

            return {

                "success": True,

                "status_code": 200,

                "message":
                    "Payment successful. "
                    "Waybill generation pending.",

                "data": {

                    "order_id":
                        str(payload.order_id),

                    "payment_status":
                        "PAID",

                    "waybill_generated":
                        False,
                },
            }

        # ========================================================
        # 9. CHECK ADDRESS
        # ========================================================

        if not order.address:

            return {

                "success": True,

                "status_code": 200,

                "message":
                    "Payment successful, "
                    "but delivery address is missing.",

                "data": {

                    "order_id":
                        str(order.id),

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
        # 10. CHECK EXISTING SHIPMENT
        # ========================================================

        existing_shipment = (
            await ShipmentRepository
            .get_by_order_id(
                db,
                order.id,
            )
        )

        if (
            existing_shipment
            and existing_shipment.tracking_number
        ):

            return {

                "success": True,

                "status_code": 200,

                "message":
                    "Payment successful. "
                    "Waybill already exists.",

                "data": {

                    "order_id":
                        str(order.id),

                    "payment_status":
                        "PAID",

                    "order_status":
                        (
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
        # 11. GENERATE WAYBILL
        # ========================================================

        try:

            # ----------------------------------------------------
            # STORE / WAREHOUSE
            # ----------------------------------------------------

            store_result = await db.execute(

                select(
                    StoreSetting
                ).limit(1)
            )

            store_setting = (
                store_result
                .scalar_one_or_none()
            )

            # ----------------------------------------------------
            # BLUE DART WAYBILL API
            # ----------------------------------------------------

            waybill_data = (
                await BlueDartService
                .generate_waybill(

                    order=order,

                    address=order.address,

                    store_setting=store_setting,
                )
            )

            # ----------------------------------------------------
            # GET AWB
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
            # 12. CREATE SHIPMENT
            # ====================================================

            shipment = (
                await ShipmentRepository
                .create_shipment(

                    db=db,

                    order_id=order.id,

                    tracking_number=awb_number,

                    courier_name="Blue Dart",

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
            )

            # ====================================================
            # 13. SAVE EXTRA SHIPPING DATA
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

            for model_field, response_field in (
                optional_fields.items()
            ):

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
            # 14. ORDER = PACKED
            # ====================================================

            order.status = (
                OrderStatus.PACKED
            )

            # ====================================================
            # 15. COMMIT EVERYTHING
            # ====================================================

            await db.commit()

            # ====================================================
            # 16. REFRESH
            # ====================================================

            await db.refresh(
                order
            )

            await db.refresh(
                shipment
            )

            # ====================================================
            # 17. RETURN
            # ====================================================

            return {

                "success": True,

                "status_code": 200,

                "message":
                    "Payment successful and "
                    "Blue Dart Waybill generated successfully.",

                "data": {

                    "order_id":
                        str(order.id),

                    "payment_id":
                        str(payment.id),

                    "razorpay_order_id":
                        payload.razorpay_order_id,

                    "razorpay_payment_id":
                        payload.razorpay_payment_id,

                    "payment_status":
                        "PAID",

                    "order_status":
                        (
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

                    "actual_weight":
                        waybill_data.get(
                            "actual_weight"
                        ),

                    "length":
                        waybill_data.get(
                            "length"
                        ),

                    "breadth":
                        waybill_data.get(
                            "breadth"
                        ),

                    "height":
                        waybill_data.get(
                            "height"
                        ),

                    "piece_count":
                        waybill_data.get(
                            "piece_count"
                        ),
                },
            }

        # ========================================================
        # BLUE DART FAILURE
        # ========================================================

        except Exception as exc:

            # ----------------------------------------------------
            # IMPORTANT
            #
            # Payment has already been committed as PAID.
            #
            # Do NOT make payment pending again.
            # ----------------------------------------------------

            await db.rollback()

            return {

                "success": True,

                "status_code": 200,

                "message":
                    "Payment successful, "
                    "but Blue Dart Waybill generation "
                    "is pending.",

                "data": {

                    "order_id":
                        str(order.id),

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