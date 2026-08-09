# app/services/admin/order_service.py

from datetime import datetime

from fastapi import HTTPException

from app.repositories.order_repository import (
    OrderRepository
)

from app.repositories.shipment_repository import (
    ShipmentRepository
)

from app.models.models import (
    PaymentStatus,
    OrderStatus,
)

from app.services.bluedart_service import (
    BlueDartService
)


class OrderService:

    # ============================================================
    # ADMIN ORDER LIST
    # ============================================================

    @staticmethod
    async def get_orders(
        db,
        page: int,
        page_size: int,
        search=None,
        status=None,
        payment_status=None,
    ):

        # --------------------------------------------------------
        # DEFAULT = PAID
        # --------------------------------------------------------

        if not payment_status:
            payment_status = PaymentStatus.PAID

        orders, total = (
            await OrderRepository.get_orders(
                db=db,
                page=page,
                page_size=page_size,
                search=search,
                status=status,
                payment_status=payment_status,
            )
        )

        summary = (
            await OrderRepository
            .get_order_summary(db)
        )

        return {

            "orders": [

                {
                    "id": str(order.id),

                    "order_number":
                        order.order_number,

                    "products": [

                        {
                            "product_id":
                                str(item.product_id),

                            "product_name":
                                item.product_name,

                            "product_sku":
                                item.product_sku,

                            "quantity":
                                item.quantity,

                            "product_image":
                                (
                                    item.product.thumbnail_url
                                    if item.product
                                    else None
                                ),
                        }

                        for item in order.items
                    ],

                    "customer_name":
                        (
                            order.user.full_name
                            if order.user
                            else None
                        ),

                    "customer_phone":
                        (
                            order.user.phone
                            if order.user
                            else None
                        ),

                    "items_count":
                        sum(
                            item.quantity
                            for item in order.items
                        ),

                    "amount":
                        float(
                            order.total_amount
                        ),

                    "payment_status":
                        (
                            order.payment_status.value
                            if order.payment_status
                            else None
                        ),

                    "status":
                        (
                            order.status.value
                            if order.status
                            else None
                        ),

                    "awb_number":
                        (
                            order.shipments[0].tracking_number
                            if order.shipments
                            else None
                        ),

                    "courier":
                        (
                            order.shipments[0].courier_name
                            if order.shipments
                            else None
                        ),

                    "shipment_status":
                        (
                            order.shipments[0].status
                            if order.shipments
                            else None
                        ),

                    "order_date":
                        order.created_at,
                }

                for order in orders
            ],

            "summary": {

                "total_orders":
                    summary["total_orders"],

                "revenue":
                    float(
                        summary["revenue"]
                    ),

                "pending":
                    summary["pending"] or 0,

                "in_transit":
                    summary["in_transit"] or 0,

                "delivered":
                    summary["delivered"] or 0,

                "cancelled":
                    summary["cancelled"] or 0,
            },

            "pagination": {

                "page": page,

                "page_size":
                    page_size,

                "total":
                    total,
            }
        }

    # ============================================================
    # ADMIN SINGLE ORDER DETAILS
    # ============================================================

    @staticmethod
    async def get_order(
        db,
        order_id,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id
            )
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        # --------------------------------------------------------
        # ONLY PAID ORDERS
        # --------------------------------------------------------

        if (
            order.payment_status
            != PaymentStatus.PAID
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only paid orders are "
                    "available in admin shipping flow."
                )
            )

        # ========================================================
        # PACKAGE CALCULATION
        # ========================================================

        total_weight = 0

        total_items = 0

        for item in order.items:

            quantity = (
                item.quantity or 1
            )

            total_items += quantity

            if (
                item.product
                and item.product.weight
            ):

                weight = float(
                    item.product.weight
                )

            else:

                weight = 0.5

            total_weight += (
                weight * quantity
            )

        total_weight = max(
            0.5,
            total_weight
        )

        # ========================================================
        # PAYMENT DETAILS
        # ========================================================

        payments = [

            {
                "payment_id":
                    str(payment.id),

                "amount":
                    float(payment.amount),

                "method":
                    (
                        payment.payment_method.value
                        if payment.payment_method
                        else None
                    ),

                "gateway":
                    (
                        payment.payment_gateway.value
                        if payment.payment_gateway
                        else None
                    ),

                "gateway_order_id":
                    payment.gateway_order_id,

                "transaction_id":
                    payment.gateway_transaction_id,

                "status":
                    (
                        payment.status.value
                        if payment.status
                        else None
                    ),

                "paid_at":
                    payment.paid_at,

                "payment_response":
                    payment.payment_response_data,
            }

            for payment in order.payments
        ]

        # ========================================================
        # SHIPMENT DETAILS
        # ========================================================

        shipments = []

        for shipment in order.shipments:

            shipments.append({

                "shipment_id":
                    str(shipment.id),

                "courier_name":
                    shipment.courier_name,

                # IMPORTANT
                "awb_number":
                    shipment.tracking_number,

                "tracking_number":
                    shipment.tracking_number,

                "pickup_token_number":
                    shipment.pickup_token_number,

                "product_code":
                    shipment.product_code,

                "sub_product_code":
                    shipment.sub_product_code,

                "pack_type":
                    shipment.pack_type,

                "cluster_code":
                    shipment.cluster_code,

                "origin_area":
                    shipment.origin_area,

                "destination_area":
                    shipment.destination_area,

                "destination_location":
                    shipment.destination_location,

                "actual_weight":
                    (
                        float(
                            shipment.actual_weight
                        )
                        if shipment.actual_weight
                        else None
                    ),

                "length":
                    (
                        float(
                            shipment.length
                        )
                        if shipment.length
                        else None
                    ),

                "breadth":
                    (
                        float(
                            shipment.breadth
                        )
                        if shipment.breadth
                        else None
                    ),

                "height":
                    (
                        float(
                            shipment.height
                        )
                        if shipment.height
                        else None
                    ),

                "piece_count":
                    shipment.piece_count,

                "status":
                    shipment.status,

                "status_code":
                    shipment.status_code,

                "last_scanned_location":
                    shipment.last_scanned_location,

                "last_scanned_at":
                    shipment.last_scanned_at,

                "estimated_delivery":
                    shipment.estimated_delivery,

                "shipped_at":
                    shipment.shipped_at,

                "delivered_at":
                    shipment.delivered_at,

                "awb_pdf_url":
                    shipment.awb_pdf_url,

                "label_pdf_url":
                    shipment.label_pdf_url,

                "mps_details":
                    shipment.mps_details,
            })

        # ========================================================
        # ITEMS
        # ========================================================

        items = [

            {
                "order_item_id":
                    str(item.id),

                "product_id":
                    str(item.product_id),

                "product_name":
                    item.product_name,

                "product_sku":
                    item.product_sku,

                "product_image":
                    (
                        item.product.thumbnail_url
                        if item.product
                        else None
                    ),

                "weight":
                    (
                        float(
                            item.product.weight
                        )
                        if (
                            item.product
                            and item.product.weight
                        )
                        else 0.5
                    ),

                "length":
                    (
                        float(
                            item.product.length
                        )
                        if (
                            item.product
                            and item.product.length
                        )
                        else 10.0
                    ),

                "breadth":
                    (
                        float(
                            item.product.breadth
                        )
                        if (
                            item.product
                            and item.product.breadth
                        )
                        else 10.0
                    ),

                "height":
                    (
                        float(
                            item.product.height
                        )
                        if (
                            item.product
                            and item.product.height
                        )
                        else 10.0
                    ),

                "quantity":
                    item.quantity,

                "price":
                    float(item.price),

                "gst_amount":
                    float(item.gst_amount),

                "total":
                    float(item.total),
            }

            for item in order.items
        ]

        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        return {

            "id":
                str(order.id),

            "order_number":
                order.order_number,

            "order_date":
                order.created_at,

            "status":
                (
                    order.status.value
                    if order.status
                    else None
                ),

            "payment_status":
                (
                    order.payment_status.value
                    if order.payment_status
                    else None
                ),

            # ----------------------------------------------------
            # CUSTOMER
            # ----------------------------------------------------

            "customer": {

                "user_id":
                    (
                        str(order.user.id)
                        if order.user
                        else None
                    ),

                "name":
                    (
                        order.user.full_name
                        if order.user
                        else None
                    ),

                "phone":
                    (
                        order.user.phone
                        if order.user
                        else None
                    ),

                "email":
                    (
                        order.user.email
                        if order.user
                        else None
                    ),
            },

            # ----------------------------------------------------
            # SHIPPING ADDRESS
            # ----------------------------------------------------

            "shipping_address": {

                "address_id":
                    (
                        str(order.address.id)
                        if order.address
                        else None
                    ),

                "full_name":
                    (
                        order.address.full_name
                        if order.address
                        else None
                    ),

                "phone":
                    (
                        order.address.phone
                        if order.address
                        else None
                    ),

                "email":
                    (
                        order.address.email
                        if order.address
                        else (
                            order.user.email
                            if order.user
                            else None
                        )
                    ),

                "address_line1":
                    (
                        order.address.address_line1
                        if order.address
                        else None
                    ),

                "address_line2":
                    (
                        order.address.address_line2
                        if order.address
                        else None
                    ),

                "landmark":
                    (
                        order.address.landmark
                        if order.address
                        else None
                    ),

                "city":
                    (
                        order.address.city
                        if order.address
                        else None
                    ),

                "state":
                    (
                        order.address.state
                        if order.address
                        else None
                    ),

                "pincode":
                    (
                        order.address.pincode
                        if order.address
                        else None
                    ),

                "country":
                    (
                        order.address.country
                        if order.address
                        else None
                    ),
            },

            # ----------------------------------------------------
            # PACKAGE
            # ----------------------------------------------------

            "package_summary": {

                "total_weight_kg":
                    total_weight,

                "total_items_count":
                    total_items,

                "is_cod":
                    (
                        any(
                            payment.payment_method.value
                            == "cod"
                            for payment
                            in order.payments
                            if payment.payment_method
                        )
                    ),
            },

            # ----------------------------------------------------
            # PRODUCTS
            # ----------------------------------------------------

            "items":
                items,

            # ----------------------------------------------------
            # PRICING
            # ----------------------------------------------------

            "pricing": {

                "subtotal":
                    float(order.subtotal),

                "gst":
                    float(order.gst_amount),

                "shipping":
                    float(order.shipping_charge),

                "discount":
                    float(order.discount),

                "grand_total":
                    float(order.total_amount),
            },

            # ----------------------------------------------------
            # PAYMENTS
            # ----------------------------------------------------

            "payments":
                payments,

            # ----------------------------------------------------
            # BLUE DART
            # ----------------------------------------------------

            "shipments":
                shipments,

            # ----------------------------------------------------
            # ORDER FINAL DATA
            # ----------------------------------------------------

            "cancel_reason":
                order.cancel_reason,

            "delivered_at":
                order.delivered_at,
        }

    # ============================================================
    # UPDATE STATUS
    # ============================================================

    @staticmethod
    async def update_status(
        db,
        order_id,
        status,
    ):

        return await (
            OrderRepository
            .update_order_status(
                db,
                order_id,
                status,
            )
        )

    # ============================================================
    # UPDATE PAYMENT STATUS
    # ============================================================

    @staticmethod
    async def update_payment_status(
        db,
        order_id,
        payment_status,
    ):

        return await (
            OrderRepository
            .update_payment_status(
                db,
                order_id,
                payment_status,
            )
        )

    # ============================================================
    # CANCEL
    # ============================================================

    @staticmethod
    async def cancel_order(
        db,
        order_id,
        reason,
    ):

        return await (
            OrderRepository
            .cancel_order(
                db,
                order_id,
                reason,
            )
        )
    

    # ============================================================
    # SYNC BLUE DART STATUS
    # ============================================================

    @staticmethod
    async def sync_shipment_status(
        db,
        order_id,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id
            )
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        # --------------------------------------------------------
        # ONLY PAID ORDERS
        # --------------------------------------------------------

        if (
            order.payment_status
            != PaymentStatus.PAID
        ):

            raise HTTPException(
                status_code=400,
                detail="Only paid orders can be tracked."
            )

        # --------------------------------------------------------
        # NO SHIPMENT
        # --------------------------------------------------------

        if not order.shipments:

            return {
                "success": True,
                "message": (
                    "Waybill has not been generated yet."
                ),
                "data": {
                    "order_id":
                        str(order.id),

                    "order_status":
                        order.status.value,

                    "awb_number":
                        None,
                }
            }

        shipment = order.shipments[0]

        # --------------------------------------------------------
        # NO AWB
        # --------------------------------------------------------

        if not shipment.tracking_number:

            return {
                "success": True,
                "message": (
                    "Waybill generation pending."
                ),
                "data": {
                    "order_id":
                        str(order.id),

                    "order_status":
                        order.status.value,

                    "awb_number":
                        None,
                }
            }

        # ========================================================
        # CALL BLUE DART
        # ========================================================

        tracking_data = (
            await BlueDartService.track_shipment(
                shipment.tracking_number
            )
        )

        # ========================================================
        # UPDATE SHIPMENT
        # ========================================================

        scans = tracking_data.get(
            "scans",
            []
        )

        if scans:

            latest = scans[0]

            blue_dart_status = (
                tracking_data.get(
                    "status"
                )
                or latest.get(
                    "scan_status"
                )
                or latest.get(
                    "status"
                )
            )

            scan_code = (
                latest.get(
                    "scan_code"
                )
                or latest.get(
                    "code"
                )
            )

            scan_type = (
                latest.get(
                    "scan_type"
                )
                or latest.get(
                    "type"
                )
            )

            # ----------------------------------------------------
            # SAVE SHIPMENT STATUS
            # ----------------------------------------------------

            shipment.status = (
                blue_dart_status
            )

            shipment.status_code = (
                str(scan_code)
                if scan_code
                else None
            )

            shipment.last_scanned_location = (
                latest.get(
                    "scanned_location"
                )
            )

            shipment.last_scanned_at = (
                latest.get(
                    "scanned_at"
                )
            )

            # ====================================================
            # MAP BLUE DART → ORDER STATUS
            # ====================================================

            status_text = (
                str(
                    blue_dart_status
                    or ""
                )
                .lower()
            )

            # ----------------------------------------------------
            # DELIVERED
            # ----------------------------------------------------

            if (
                "delivered"
                in status_text
                or scan_type == "DL"
                or scan_code == "DL"
            ):

                order.status = (
                    OrderStatus.DELIVERED
                )

                shipment.status = (
                    blue_dart_status
                    or "DELIVERED"
                )

                shipment.delivered_at = (
                    latest.get(
                        "scanned_at"
                    )
                    or datetime.utcnow()
                )

                order.delivered_at = (
                    shipment.delivered_at
                )

            # ----------------------------------------------------
            # OUT FOR DELIVERY
            # ----------------------------------------------------

            elif (
                "out for delivery"
                in status_text
                or "out-for-delivery"
                in status_text
            ):

                order.status = (
                    OrderStatus.OUT_FOR_DELIVERY
                )

            # ----------------------------------------------------
            # SHIPPED / IN TRANSIT
            # ----------------------------------------------------

            elif (
                "transit"
                in status_text
                or "shipped"
                in status_text
                or "dispatched"
                in status_text
            ):

                order.status = (
                    OrderStatus.SHIPPED
                )

                if not shipment.shipped_at:

                    shipment.shipped_at = (
                        latest.get(
                            "scanned_at"
                        )
                        or datetime.utcnow()
                    )

            # ----------------------------------------------------
            # PICKUP / REGISTERED
            # ----------------------------------------------------

            elif (
                "pickup"
                in status_text
                or "registered"
                in status_text
            ):

                if order.status in (
                    OrderStatus.CONFIRMED,
                    OrderStatus.PACKED,
                ):

                    order.status = (
                        OrderStatus.PACKED
                    )

            # ====================================================
            # SAVE SCAN LOGS
            # ====================================================

            await ShipmentRepository.save_scan_logs(
                db,
                shipment.id,
                scans
            )

        # ========================================================
        # COMMIT
        # ========================================================

        await db.commit()

        # ========================================================
        # REFRESH
        # ========================================================

        await db.refresh(
            shipment
        )

        await db.refresh(
            order
        )

        return {

            "success": True,

            "message": (
                "Blue Dart tracking synchronized successfully."
            ),

            "data": {

                "order_id":
                    str(order.id),

                "order_number":
                    order.order_number,

                "order_status":
                    (
                        order.status.value
                        if order.status
                        else None
                    ),

                "payment_status":
                    (
                        order.payment_status.value
                        if order.payment_status
                        else None
                    ),

                "delivered":
                    (
                        order.status
                        == OrderStatus.DELIVERED
                    ),

                "delivered_at":
                    order.delivered_at,

                "shipment": {

                    "shipment_id":
                        str(shipment.id),

                    "courier":
                        shipment.courier_name,

                    "awb_number":
                        shipment.tracking_number,

                    "tracking_number":
                        shipment.tracking_number,

                    "status":
                        shipment.status,

                    "status_code":
                        shipment.status_code,

                    "last_scanned_location":
                        shipment.last_scanned_location,

                    "last_scanned_at":
                        shipment.last_scanned_at,

                    "estimated_delivery":
                        shipment.estimated_delivery,

                    "shipped_at":
                        shipment.shipped_at,

                    "delivered_at":
                        shipment.delivered_at,
                },

                "blue_dart_tracking":
                    tracking_data,
            }
        }