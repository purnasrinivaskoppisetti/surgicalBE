# app/services/shipping_tracking_service.py

import logging
from datetime import datetime

from app.models.models import (
    OrderStatus,
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


logger = logging.getLogger(
    "surgical.shipping_tracking"
)


class ShippingTrackingService:

    @staticmethod
    async def update_all_shipments(db):

        logger.info(
            "Searching for shipments that require tracking..."
        )

        # ========================================================
        # GET ORDERS
        # ========================================================

        orders = (
            await OrderRepository
            .get_orders_for_tracking(
                db
            )
        )

        logger.info(
            "Found %s orders requiring tracking",
            len(orders),
        )

        result = {

            "checked": 0,

            "updated": 0,

            "delivered": 0,

            "failed": 0,

            "skipped": 0,
        }

        # ========================================================
        # PROCESS EACH ORDER
        # ========================================================

        for order in orders:

            result["checked"] += 1

            logger.info(
                "Checking order=%s",
                order.order_number,
            )

            # ----------------------------------------------------
            # CHECK SHIPMENT
            # ----------------------------------------------------

            if not order.shipments:

                logger.info(
                    "Order=%s has no shipment. Skipping.",
                    order.order_number,
                )

                result["skipped"] += 1

                continue

            # ----------------------------------------------------
            # GET SHIPMENT
            # ----------------------------------------------------

            shipment = order.shipments[0]

            # ----------------------------------------------------
            # CHECK AWB
            # ----------------------------------------------------

            if not shipment.tracking_number:

                logger.info(
                    "Order=%s has no AWB. Skipping.",
                    order.order_number,
                )

                result["skipped"] += 1

                continue

            awb = shipment.tracking_number

            logger.info(
                "Tracking order=%s | AWB=%s",
                order.order_number,
                awb,
            )

            try:

                # ====================================================
                # CALL BLUE DART
                # ====================================================

                tracking_data = (
                    await BlueDartService
                    .track_shipment(
                        awb
                    )
                )

                logger.info(
                    "Blue Dart response received | "
                    "Order=%s | AWB=%s",
                    order.order_number,
                    awb,
                )

                # ====================================================
                # SCANS
                # ====================================================

                scans = (
                    tracking_data.get(
                        "scans",
                        []
                    )
                )

                if not scans:

                    logger.warning(
                        "No scans returned | "
                        "Order=%s | AWB=%s",
                        order.order_number,
                        awb,
                    )

                    result["skipped"] += 1

                    continue

                # ====================================================
                # LATEST SCAN
                # ====================================================

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

                scanned_location = (
                    latest.get(
                        "scanned_location"
                    )
                )

                scanned_at = (
                    latest.get(
                        "scanned_at"
                    )
                )

                logger.info(
                    "Latest Blue Dart status | "
                    "Order=%s | AWB=%s | "
                    "Status=%s | Code=%s | Location=%s",
                    order.order_number,
                    awb,
                    blue_dart_status,
                    scan_code,
                    scanned_location,
                )

                # ====================================================
                # UPDATE SHIPMENT
                # ====================================================

                shipment.status = (
                    blue_dart_status
                )

                shipment.status_code = (

                    str(scan_code)

                    if scan_code

                    else None
                )

                shipment.last_scanned_location = (
                    scanned_location
                )

                shipment.last_scanned_at = (
                    scanned_at
                )

                # ====================================================
                # STATUS TEXT
                # ====================================================

                status_text = (

                    str(
                        blue_dart_status
                        or ""
                    )
                    .lower()
                )

                # ====================================================
                # DELIVERED
                # ====================================================

                is_delivered = (

                    "delivered"
                    in status_text

                    or scan_type == "DL"

                    or scan_code == "DL"
                )

                if is_delivered:

                    logger.info(
                        "ORDER DELIVERED | "
                        "Order=%s | AWB=%s",
                        order.order_number,
                        awb,
                    )

                    order.status = (
                        OrderStatus.DELIVERED
                    )

                    delivery_time = (

                        scanned_at

                        or datetime.utcnow()
                    )

                    shipment.delivered_at = (
                        delivery_time
                    )

                    order.delivered_at = (
                        delivery_time
                    )

                    result["delivered"] += 1

                # ====================================================
                # OUT FOR DELIVERY
                # ====================================================

                elif (

                    "out for delivery"
                    in status_text

                    or
                    "out-for-delivery"
                    in status_text
                ):

                    logger.info(
                        "ORDER OUT FOR DELIVERY | "
                        "Order=%s | AWB=%s",
                        order.order_number,
                        awb,
                    )

                    order.status = (
                        OrderStatus.OUT_FOR_DELIVERY
                    )

                    result["updated"] += 1

                # ====================================================
                # IN TRANSIT
                # ====================================================

                elif (

                    "transit"
                    in status_text

                    or
                    "shipped"
                    in status_text

                    or
                    "dispatched"
                    in status_text
                ):

                    logger.info(
                        "ORDER IN TRANSIT | "
                        "Order=%s | AWB=%s",
                        order.order_number,
                        awb,
                    )

                    order.status = (
                        OrderStatus.SHIPPED
                    )

                    if not shipment.shipped_at:

                        shipment.shipped_at = (

                            scanned_at

                            or datetime.utcnow()
                        )

                    result["updated"] += 1

                # ====================================================
                # PICKUP / REGISTERED
                # ====================================================

                elif (

                    "pickup"
                    in status_text

                    or
                    "registered"
                    in status_text
                ):

                    logger.info(
                        "ORDER PICKUP/REGISTERED | "
                        "Order=%s | AWB=%s",
                        order.order_number,
                        awb,
                    )

                    if order.status in (

                        OrderStatus.CONFIRMED,

                        OrderStatus.PACKED,
                    ):

                        order.status = (
                            OrderStatus.PACKED
                        )

                    result["updated"] += 1

                # ====================================================
                # SAVE SCAN LOGS
                # ====================================================

                await (
                    ShipmentRepository
                    .save_scan_logs(
                        db,

                        shipment.id,

                        scans,
                    )
                )

                # ====================================================
                # COMMIT
                # ====================================================

                await db.commit()

                logger.info(
                    "Database updated | "
                    "Order=%s | AWB=%s",
                    order.order_number,
                    awb,
                )

            except Exception:

                await db.rollback()

                result["failed"] += 1

                logger.exception(
                    "Tracking failed | "
                    "Order=%s | AWB=%s",
                    order.order_number,
                    awb,
                )

        # ========================================================
        # FINAL RESULT
        # ========================================================

        logger.info(
            "Tracking job summary | "
            "Checked=%s | "
            "Updated=%s | "
            "Delivered=%s | "
            "Skipped=%s | "
            "Failed=%s",
            result["checked"],
            result["updated"],
            result["delivered"],
            result["skipped"],
            result["failed"],
        )

        return result