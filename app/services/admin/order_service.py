from datetime import datetime

from fastapi import HTTPException

from app.repositories.order_repository import (
    OrderRepository,
)

from app.repositories.shipment_repository import (
    ShipmentRepository,
)

from app.models.models import (
    PaymentStatus,
    OrderStatus,
)

from app.services.bluedart_service import (
    BlueDartService,
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
        # DEFAULT PAYMENT FILTER = PAID
        # --------------------------------------------------------

        if not payment_status:
            payment_status = PaymentStatus.PAID

        # --------------------------------------------------------
        # GET ORDERS
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # SUMMARY
        # --------------------------------------------------------

        summary = (
            await OrderRepository
            .get_order_summary(db)
        )

        # ========================================================
        # BUILD ORDER RESPONSE
        # ========================================================

        order_list = []

        for order in orders:

            # ----------------------------------------------------
            # ORDER STATUS
            # ----------------------------------------------------

            order_status = (
                order.status.value
                if order.status
                else None
            )

            # ----------------------------------------------------
            # PAYMENT STATUS
            # ----------------------------------------------------

            payment_status_value = (
                order.payment_status.value
                if order.payment_status
                else None
            )

            # ----------------------------------------------------
            # SHIPMENT
            #
            # We use the first shipment as the current shipment.
            # ----------------------------------------------------

            shipment = (
                order.shipments[0]
                if order.shipments
                else None
            )

            # ----------------------------------------------------
            # SHIPMENT STATUS
            # ----------------------------------------------------

            shipment_status = (
                shipment.status
                if shipment
                else None
            )

            # ----------------------------------------------------
            # CURRENT LOCATION
            # ----------------------------------------------------

            current_location = (
                shipment.last_scanned_location
                if shipment
                else None
            )

            # ----------------------------------------------------
            # AWB
            # ----------------------------------------------------

            awb_number = (
                shipment.tracking_number
                if shipment
                else None
            )

            # ----------------------------------------------------
            # TRACKING HISTORY
            #
            # Keep the order list lightweight.
            # We return the latest tracking information here.
            # Complete history is returned by get_order().
            # ----------------------------------------------------

            latest_scan = None

            if shipment:

                latest_scan = (
                    await ShipmentRepository
                    .get_latest_scan(
                        db,
                        shipment.id,
                    )
                )

            # ----------------------------------------------------
            # FALLBACK TO LATEST SCAN
            # ----------------------------------------------------

            if latest_scan:

                if not shipment_status:
                    shipment_status = (
                        latest_scan.scan_status
                    )

                if not current_location:
                    current_location = (
                        latest_scan.scanned_location
                    )

            # ----------------------------------------------------
            # ORDER STATUS HISTORY
            # ----------------------------------------------------

            status_history = []

            try:

                history_rows = (
                    await OrderRepository
                    .get_order_status_history(
                        db,
                        order.id,
                    )
                )

                status_history = [

                    {
                        "status":
                            (
                                history.status.value
                                if history.status
                                else None
                            ),

                        "note":
                            history.note,

                        "created_at":
                            history.created_at,
                    }

                    for history in history_rows
                ]

            except AttributeError:
                # If status_history repository method/
                # relationship isn't available, don't break
                # the order list.
                status_history = []

            # ----------------------------------------------------
            # PRODUCTS
            # ----------------------------------------------------

            products = [

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
            ]

            # ----------------------------------------------------
            # ORDER OBJECT
            # ----------------------------------------------------

            order_list.append({

                "id":
                    str(order.id),

                "order_number":
                    order.order_number,

                # ------------------------------------------------
                # ORDER STATUS
                # ------------------------------------------------

                "status":
                    order_status,

                "order_status":
                    order_status,

                # ------------------------------------------------
                # PAYMENT STATUS
                # ------------------------------------------------

                "payment_status":
                    payment_status_value,

                # ------------------------------------------------
                # CUSTOMER
                # ------------------------------------------------

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

                # ------------------------------------------------
                # ITEMS
                # ------------------------------------------------

                "items_count":
                    sum(
                        item.quantity
                        for item in order.items
                    ),

                "products":
                    products,

                # ------------------------------------------------
                # AMOUNT
                # ------------------------------------------------

                "amount":
                    float(
                        order.total_amount
                    ),

                # ------------------------------------------------
                # SHIPMENT / WAYBILL
                # ------------------------------------------------

                "shipment": {

                    "shipment_id":
                        (
                            str(shipment.id)
                            if shipment
                            else None
                        ),

                    "courier":
                        (
                            shipment.courier_name
                            if shipment
                            else None
                        ),

                    "courier_name":
                        (
                            shipment.courier_name
                            if shipment
                            else None
                        ),

                    "awb_number":
                        awb_number,

                    "tracking_number":
                        awb_number,

                    "waybill_generated":
                        bool(
                            awb_number
                        ),

                    "waybill_status":
                        shipment_status,

                    "status":
                        shipment_status,

                    "status_code":
                        (
                            shipment.status_code
                            if shipment
                            else None
                        ),

                    "current_location":
                        current_location,

                    "last_scanned_location":
                        (
                            shipment.last_scanned_location
                            if shipment
                            else None
                        ),

                    "last_scanned_at":
                        (
                            shipment.last_scanned_at
                            if shipment
                            else None
                        ),

                    "estimated_delivery":
                        (
                            shipment.estimated_delivery
                            if shipment
                            else None
                        ),

                    "shipped_at":
                        (
                            shipment.shipped_at
                            if shipment
                            else None
                        ),

                    "delivered_at":
                        (
                            shipment.delivered_at
                            if shipment
                            else None
                        ),
                },

                # ------------------------------------------------
                # QUICK WAYBILL FIELDS
                # ------------------------------------------------

                "awb_number":
                    awb_number,

                "courier":
                    (
                        shipment.courier_name
                        if shipment
                        else None
                    ),

                "shipment_status":
                    shipment_status,

                "current_location":
                    current_location,

                # ------------------------------------------------
                # ORDER STATUS HISTORY
                # ------------------------------------------------

                "status_history":
                    status_history,

                # ------------------------------------------------
                # DATE
                # ------------------------------------------------

                "order_date":
                    order.created_at,
            })

        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        return {

            "orders":
                order_list,

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

                "page":
                    page,

                "page_size":
                    page_size,

                "total":
                    total,
            },
        }

    # ============================================================
    # ADMIN SINGLE ORDER DETAILS
    # ============================================================

    @staticmethod
    async def get_order(
        db,
        order_id,
    ):

        # --------------------------------------------------------
        # GET ORDER
        # --------------------------------------------------------

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id,
            )
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
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
                ),
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
            total_weight,
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

            # ----------------------------------------------------
            # COMPLETE BLUE DART HISTORY
            # ----------------------------------------------------

            scan_logs = (
                await ShipmentRepository
                .get_scan_logs(
                    db,
                    shipment.id,
                )
            )

            # ----------------------------------------------------
            # TRACKING HISTORY
            # ----------------------------------------------------

            tracking_history = [

                {
                    "scan_id":
                        str(scan.id),

                    "status":
                        scan.scan_status,

                    "status_code":
                        scan.scan_code,

                    "scan_type":
                        scan.scan_type,

                    "scan_group_type":
                        scan.scan_group_type,

                    "location":
                        scan.scanned_location,

                    "scanned_location":
                        scan.scanned_location,

                    "scanned_at":
                        scan.scanned_at,
                }

                for scan in scan_logs
            ]

            # ----------------------------------------------------
            # LATEST SCAN
            # ----------------------------------------------------

            latest_scan = (
                scan_logs[0]
                if scan_logs
                else None
            )

            # ----------------------------------------------------
            # CURRENT STATUS
            # ----------------------------------------------------

            current_status = (
                shipment.status
            )

            if (
                not current_status
                and latest_scan
            ):

                current_status = (
                    latest_scan.scan_status
                )

            # ----------------------------------------------------
            # CURRENT LOCATION
            # ----------------------------------------------------

            current_location = (
                shipment.last_scanned_location
            )

            if (
                not current_location
                and latest_scan
            ):

                current_location = (
                    latest_scan.scanned_location
                )

            # ----------------------------------------------------
            # CURRENT STATUS CODE
            # ----------------------------------------------------

            current_status_code = (
                shipment.status_code
            )

            if (
                not current_status_code
                and latest_scan
            ):

                current_status_code = (
                    latest_scan.scan_code
                )

            # ----------------------------------------------------
            # LAST SCAN TIME
            # ----------------------------------------------------

            last_scanned_at = (
                shipment.last_scanned_at
            )

            if (
                not last_scanned_at
                and latest_scan
            ):

                last_scanned_at = (
                    latest_scan.scanned_at
                )

            # ----------------------------------------------------
            # SHIPMENT
            # ----------------------------------------------------

            shipments.append({

                "shipment_id":
                    str(shipment.id),

                # ------------------------------------------------
                # COURIER
                # ------------------------------------------------

                "courier_name":
                    shipment.courier_name,

                "courier":
                    shipment.courier_name,

                # ------------------------------------------------
                # AWB
                # ------------------------------------------------

                "awb_number":
                    shipment.tracking_number,

                "tracking_number":
                    shipment.tracking_number,

                "waybill_generated":
                    bool(
                        shipment.tracking_number
                    ),

                # ------------------------------------------------
                # WAYBILL STATUS
                # ------------------------------------------------

                "waybill_status":
                    current_status,

                "status":
                    current_status,

                "status_code":
                    current_status_code,

                # ------------------------------------------------
                # LOCATION
                # ------------------------------------------------

                "current_location":
                    current_location,

                "last_scanned_location":
                    shipment.last_scanned_location,

                "last_scanned_at":
                    last_scanned_at,

                # ------------------------------------------------
                # DELIVERY
                # ------------------------------------------------

                "estimated_delivery":
                    shipment.estimated_delivery,

                "shipped_at":
                    shipment.shipped_at,

                "delivered_at":
                    shipment.delivered_at,

                # ------------------------------------------------
                # BLUE DART DATA
                # ------------------------------------------------

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

                # ------------------------------------------------
                # PACKAGE
                # ------------------------------------------------

                "actual_weight":
                    (
                        float(
                            shipment.actual_weight
                        )
                        if shipment.actual_weight
                        is not None
                        else None
                    ),

                "length":
                    (
                        float(
                            shipment.length
                        )
                        if shipment.length
                        is not None
                        else None
                    ),

                "breadth":
                    (
                        float(
                            shipment.breadth
                        )
                        if shipment.breadth
                        is not None
                        else None
                    ),

                "height":
                    (
                        float(
                            shipment.height
                        )
                        if shipment.height
                        is not None
                        else None
                    ),

                "piece_count":
                    shipment.piece_count,

                # ------------------------------------------------
                # DOCUMENTS
                # ------------------------------------------------

                "awb_pdf_url":
                    shipment.awb_pdf_url,

                "label_pdf_url":
                    shipment.label_pdf_url,

                # ------------------------------------------------
                # MPS
                # ------------------------------------------------

                "mps_details":
                    shipment.mps_details,

                # ------------------------------------------------
                # COMPLETE TRACKING
                # ------------------------------------------------

                "tracking_count":
                    len(tracking_history),

                "tracking_history":
                    tracking_history,
            })

        # ========================================================
        # ORDER STATUS HISTORY
        # ========================================================

        status_history = []

        try:

            history_rows = (
                await OrderRepository
                .get_order_status_history(
                    db,
                    order.id,
                )
            )

            status_history = [

                {
                    "status":
                        (
                            history.status.value
                            if history.status
                            else None
                        ),

                    "note":
                        history.note,

                    "created_at":
                        history.created_at,
                }

                for history in history_rows
            ]

        except AttributeError:

            status_history = []

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
        # CURRENT ORDER STATUS
        # ========================================================

        order_status = (
            order.status.value
            if order.status
            else None
        )

        # ========================================================
        # CURRENT PAYMENT STATUS
        # ========================================================

        current_payment_status = (
            order.payment_status.value
            if order.payment_status
            else None
        )

        # ========================================================
        # CURRENT SHIPMENT SUMMARY
        # ========================================================

        current_shipment = (
            shipments[0]
            if shipments
            else None
        )

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

            # ====================================================
            # MAIN STATUSES
            # ====================================================

            "status":
                order_status,

            "order_status":
                order_status,

            "payment_status":
                current_payment_status,

            # ====================================================
            # STATUS SUMMARY
            # ====================================================

            "status_summary": {

                "order_status":
                    order_status,

                "payment_status":
                    current_payment_status,

                "waybill_generated":
                    (
                        current_shipment[
                            "waybill_generated"
                        ]
                        if current_shipment
                        else False
                    ),

                "waybill_status":
                    (
                        current_shipment[
                            "waybill_status"
                        ]
                        if current_shipment
                        else None
                    ),

                "awb_number":
                    (
                        current_shipment[
                            "awb_number"
                        ]
                        if current_shipment
                        else None
                    ),

                "courier":
                    (
                        current_shipment[
                            "courier"
                        ]
                        if current_shipment
                        else None
                    ),

                "current_location":
                    (
                        current_shipment[
                            "current_location"
                        ]
                        if current_shipment
                        else None
                    ),

                "last_scanned_at":
                    (
                        current_shipment[
                            "last_scanned_at"
                        ]
                        if current_shipment
                        else None
                    ),

                "estimated_delivery":
                    (
                        current_shipment[
                            "estimated_delivery"
                        ]
                        if current_shipment
                        else None
                    ),
            },

            # ====================================================
            # CUSTOMER
            # ====================================================

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

            # ====================================================
            # SHIPPING ADDRESS
            # ====================================================

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

            # ====================================================
            # PACKAGE
            # ====================================================

            "package_summary": {

                "total_weight_kg":
                    total_weight,

                "total_items_count":
                    total_items,

                "is_cod":
                    any(
                        payment.payment_method.value
                        == "cod"
                        for payment
                        in order.payments
                        if payment.payment_method
                    ),
            },

            # ====================================================
            # PRODUCTS
            # ====================================================

            "items":
                items,

            # ====================================================
            # PRICING
            # ====================================================

            "pricing": {

                "subtotal":
                    float(
                        order.subtotal
                    ),

                "gst":
                    float(
                        order.gst_amount
                    ),

                "shipping":
                    float(
                        order.shipping_charge
                    ),

                "discount":
                    float(
                        order.discount
                    ),

                "grand_total":
                    float(
                        order.total_amount
                    ),
            },

            # ====================================================
            # PAYMENTS
            # ====================================================

            "payments":
                payments,

            # ====================================================
            # COMPLETE SHIPMENT INFORMATION
            # ====================================================

            "shipments":
                shipments,

            # ====================================================
            # ORDER STATUS HISTORY
            # ====================================================

            "status_history":
                status_history,

            # ====================================================
            # FINAL ORDER DATA
            # ====================================================

            "cancel_reason":
                order.cancel_reason,

            "delivered_at":
                order.delivered_at,
        }

    # ============================================================
    # UPDATE ORDER STATUS
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
    # CANCEL ORDER
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

        # --------------------------------------------------------
        # GET ORDER
        # --------------------------------------------------------

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id,
            )
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
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
                    "Only paid orders can be tracked."
                ),
            )

        # --------------------------------------------------------
        # NO SHIPMENT
        # --------------------------------------------------------

        if not order.shipments:

            return {

                "success":
                    True,

                "message":
                    "Waybill has not been generated yet.",

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

                    "awb_number":
                        None,

                    "waybill_generated":
                        False,
                },
            }

        # --------------------------------------------------------
        # CURRENT SHIPMENT
        # --------------------------------------------------------

        shipment = order.shipments[0]

        # --------------------------------------------------------
        # NO AWB
        # --------------------------------------------------------

        if not shipment.tracking_number:

            return {

                "success":
                    True,

                "message":
                    "Waybill generation pending.",

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

                    "awb_number":
                        None,

                    "waybill_generated":
                        False,
                },
            }

        # ========================================================
        # CALL BLUE DART
        # ========================================================

        tracking_data = (
            await BlueDartService
            .track_shipment(
                shipment.tracking_number
            )
        )

        # ========================================================
        # UPDATE SHIPMENT
        # ========================================================

        scans = tracking_data.get(
            "scans",
            [],
        )

        if scans:

            # ----------------------------------------------------
            # ASSUME BLUE DART RETURNS LATEST FIRST
            # ----------------------------------------------------

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
            # UPDATE CURRENT BLUE DART STATUS
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
                or latest.get(
                    "location"
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
            # SAVE ALL BLUE DART SCANS
            # ====================================================

            await ShipmentRepository.save_scan_logs(
                db,
                shipment.id,
                scans,
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

        # ========================================================
        # GET COMPLETE TRACKING HISTORY
        # ========================================================

        tracking_history = (
            await ShipmentRepository
            .get_tracking_history(
                db,
                shipment.id,
            )
        )

        # ========================================================
        # FINAL RESPONSE
        # ========================================================

        return {

            "success":
                True,

            "message":
                (
                    "Blue Dart tracking "
                    "synchronized successfully."
                ),

            "data": {

                # ------------------------------------------------
                # ORDER
                # ------------------------------------------------

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

                # ------------------------------------------------
                # PAYMENT
                # ------------------------------------------------

                "payment_status":
                    (
                        order.payment_status.value
                        if order.payment_status
                        else None
                    ),

                # ------------------------------------------------
                # DELIVERY
                # ------------------------------------------------

                "delivered":
                    (
                        order.status
                        == OrderStatus.DELIVERED
                    ),

                "delivered_at":
                    order.delivered_at,

                # ------------------------------------------------
                # SHIPMENT
                # ------------------------------------------------

                "shipment": {

                    "shipment_id":
                        str(shipment.id),

                    "courier":
                        shipment.courier_name,

                    "awb_number":
                        shipment.tracking_number,

                    "tracking_number":
                        shipment.tracking_number,

                    "waybill_generated":
                        bool(
                            shipment.tracking_number
                        ),

                    "waybill_status":
                        shipment.status,

                    "status":
                        shipment.status,

                    "status_code":
                        shipment.status_code,

                    "current_location":
                        shipment.last_scanned_location,

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

                # ------------------------------------------------
                # COMPLETE TRACKING HISTORY
                # ------------------------------------------------

                "tracking_history":
                    tracking_history,

                "tracking_count":
                    len(tracking_history),

                # ------------------------------------------------
                # RAW BLUE DART RESPONSE
                # ------------------------------------------------

                "blue_dart_tracking":
                    tracking_data,
            },
        }