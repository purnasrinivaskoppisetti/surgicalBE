# app/api/routes/shipping_routes.py

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db,
    get_current_user,
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


router = APIRouter(
    prefix="/shipping",
    tags=["Customer Shipping"],
)


# ================================================================
# HELPER - GET USER ID
# ================================================================

def _extract_user_id(user_obj) -> UUID | str:
    """
    Safely extract authenticated user ID.

    Supports:
        - ORM user object
        - dictionary/JWT payload
        - UUID
        - string
    """

    # ORM object
    if hasattr(user_obj, "id") and user_obj.id:
        return user_obj.id

    # Dictionary / JWT payload
    if isinstance(user_obj, dict):

        raw_id = (
            user_obj.get("id")
            or user_obj.get("sub")
            or user_obj.get("user_id")
        )

        if raw_id:
            return raw_id

    # UUID / string
    if isinstance(user_obj, (str, UUID)):
        return user_obj

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not resolve authenticated user identity.",
    )


# ================================================================
# CHECK SERVICEABILITY
# ================================================================

@router.get(
    "/check-serviceability"
)
async def check_pincode(
    pincode: str = Query(
        ...,
        min_length=6,
        max_length=6,
        example="534281",
        description="Customer destination pincode",
    )
):
    """
    Check whether Blue Dart delivers
    to the customer's pincode.
    """

    return await BlueDartService.check_serviceability(
        pincode=pincode
    )


# ================================================================
# ESTIMATE DELIVERY
# ================================================================

@router.get(
    "/estimate-delivery"
)
async def estimate_delivery_date(
    pincode: str = Query(
        ...,
        min_length=6,
        max_length=6,
        description="Customer destination pincode",
    ),

    is_cod: bool = Query(
        False,
        description=(
            "True for Cash on Delivery, "
            "False for prepaid"
        ),
    ),
):
    """
    Get estimated delivery date before order placement.
    """

    sub_product = (
        "C"
        if is_cod
        else "P"
    )

    return await BlueDartService.get_transit_time(
        destination_pincode=pincode,
        sub_product_code=sub_product,
    )


# ================================================================
# TRACK USING AWB
# ================================================================

@router.get(
    "/track/{awb_number}"
)
async def track_shipment_by_awb(
    awb_number: str,

    db: AsyncSession = Depends(
        get_db
    ),
):
    """
    Track shipment directly using Blue Dart AWB number.

    This can be used by:
        - customer
        - admin
        - support team

    Example:

    GET /api/v1/shipping/track/77113180476
    """

    if not awb_number.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AWB number is required.",
        )

    # ============================================================
    # CALL BLUE DART
    # ============================================================

    tracking_data = (
        await BlueDartService.track_shipment(
            awb_number=awb_number.strip()
        )
    )

    # ============================================================
    # FIND LOCAL SHIPMENT
    # ============================================================

    shipment = (
        await ShipmentRepository.get_by_awb(
            db,
            awb_number.strip()
        )
    )

    # ============================================================
    # UPDATE LOCAL SHIPMENT
    # ============================================================

    if shipment:

        scans = tracking_data.get(
            "scans",
            []
        )

        shipment.status = (
            tracking_data.get(
                "status"
            )
            or shipment.status
        )

        # Latest scan
        if scans:

            latest_scan = scans[0]

            shipment.last_scanned_location = (
                latest_scan.get(
                    "scanned_location"
                )
            )

            shipment.last_scanned_at = (
                latest_scan.get(
                    "scanned_at"
                )
            )

            # Save scan history
            await ShipmentRepository.save_scan_logs(
                db,
                shipment.id,
                scans,
            )

        # Commit shipment status/location
        await db.commit()

        await db.refresh(
            shipment
        )

    # ============================================================
    # RESPONSE
    # ============================================================

    return {
        "success": True,

        "message": (
            "Shipment tracking information "
            "retrieved successfully."
        ),

        "data": {

            "awb_number": (
                tracking_data.get(
                    "awb_number"
                )
            ),

            "status": (
                tracking_data.get(
                    "status"
                )
            ),

            "origin": (
                tracking_data.get(
                    "origin"
                )
            ),

            "destination": (
                tracking_data.get(
                    "destination"
                )
            ),

            "scans": (
                tracking_data.get(
                    "scans",
                    []
                )
            ),
        },
    }


# ================================================================
# TRACK CUSTOMER ORDER
# ================================================================

@router.get(
    "/track-order/{order_id}"
)
async def track_my_order(
    order_id: UUID,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),
):
    """
    Customer order tracking.

    Customer sends:
        order_id

    Backend:
        1. Authenticates customer
        2. Checks order ownership
        3. Finds shipment
        4. Gets AWB
        5. Calls Blue Dart
        6. Updates local shipment
        7. Saves scan history
        8. Returns live tracking data
    """

    # ============================================================
    # 1. GET AUTHENTICATED USER
    # ============================================================

    user_id = _extract_user_id(
        current_user
    )

    # ============================================================
    # 2. GET ORDER
    # ============================================================

    order = await OrderRepository.get_customer_order(
        db=db,
        order_id=order_id,
        user_id=user_id,
    )

    if not order:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    # ============================================================
    # 3. FIND SHIPMENT
    # ============================================================

    shipment = (
        await ShipmentRepository.get_by_order_id(
            db,
            order_id
        )
    )

    # ============================================================
    # 4. WAYBILL NOT GENERATED
    # ============================================================

    if (
        not shipment
        or not shipment.tracking_number
    ):

        order_status = getattr(
            order,
            "status",
            "PROCESSING",
        )

        if hasattr(
            order_status,
            "value",
        ):
            order_status = (
                order_status.value
            )

        return {
            "success": True,

            "message": (
                "Order is currently being prepared. "
                "Shipping/Waybill generation is pending."
            ),

            "data": {

                "order_id": str(
                    order.id
                ),

                "order_number": (
                    getattr(
                        order,
                        "order_number",
                        None,
                    )
                ),

                "order_status": (
                    order_status
                ),

                "shipment_created": False,

                "awb_number": None,

                "courier": None,

                "tracking_status": (
                    "WAYBILL_PENDING"
                ),

                "origin": None,

                "destination": None,

                "scans": [],
            },
        }

    # ============================================================
    # 5. GET AWB
    # ============================================================

    awb_number = (
        shipment.tracking_number.strip()
    )

    # ============================================================
    # 6. CALL BLUE DART
    # ============================================================

    try:

        tracking_data = (
            await BlueDartService.track_shipment(
                awb_number=awb_number
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Unable to fetch shipment tracking "
                f"information: {str(exc)}"
            ),
        )

    # ============================================================
    # 7. UPDATE LOCAL SHIPMENT
    # ============================================================

    scans = tracking_data.get(
        "scans",
        []
    )

    tracking_status = (
        tracking_data.get(
            "status"
        )
    )

    if tracking_status:

        shipment.status = tracking_status

    # ============================================================
    # 8. SAVE LATEST SCAN
    # ============================================================

    if scans:

        latest_scan = scans[0]

        shipment.last_scanned_location = (
            latest_scan.get(
                "scanned_location"
            )
        )

        shipment.last_scanned_at = (
            latest_scan.get(
                "scanned_at"
            )
        )

        # Save tracking history
        await ShipmentRepository.save_scan_logs(
            db,
            shipment.id,
            scans,
        )

    # ============================================================
    # 9. COMMIT LOCAL TRACKING DATA
    # ============================================================

    try:

        await db.commit()

        await db.refresh(
            shipment
        )

    except Exception as exc:

        await db.rollback()

        # Important:
        # Tracking from Blue Dart was successful.
        # Local DB update failed.
        #
        # We don't hide the live tracking result.

        return {
            "success": True,

            "message": (
                "Live tracking retrieved, "
                "but local tracking cache could not "
                "be updated."
            ),

            "data": {

                "order_id": str(
                    order.id
                ),

                "order_number": (
                    order.order_number
                ),

                "shipment_id": str(
                    shipment.id
                ),

                "courier": (
                    shipment.courier_name
                ),

                "awb_number": (
                    awb_number
                ),

                "tracking_status": (
                    tracking_status
                ),

                "origin": (
                    tracking_data.get(
                        "origin"
                    )
                ),

                "destination": (
                    tracking_data.get(
                        "destination"
                    )
                ),

                "scans": scans,

                "database_sync_error": str(
                    exc
                ),
            },
        }

    # ============================================================
    # 10. ORDER STATUS
    # ============================================================

    order_status = getattr(
        order,
        "status",
        "PROCESSING",
    )

    if hasattr(
        order_status,
        "value",
    ):
        order_status = (
            order_status.value
        )

    # ============================================================
    # 11. FINAL RESPONSE
    # ============================================================

    return {
        "success": True,

        "message": (
            "Live shipment tracking "
            "retrieved successfully."
        ),

        "data": {

            # ----------------------------------------------------
            # ORDER
            # ----------------------------------------------------

            "order_id": str(
                order.id
            ),

            "order_number": (
                order.order_number
            ),

            "order_status": (
                order_status
            ),

            # ----------------------------------------------------
            # SHIPMENT
            # ----------------------------------------------------

            "shipment_id": str(
                shipment.id
            ),

            "courier": (
                shipment.courier_name
            ),

            "awb_number": (
                awb_number
            ),

            "pickup_token_number": (
                shipment.pickup_token_number
            ),

            # ----------------------------------------------------
            # TRACKING
            # ----------------------------------------------------

            "tracking_status": (
                tracking_status
            ),

            "origin": (
                tracking_data.get(
                    "origin"
                )
            ),

            "destination": (
                tracking_data.get(
                    "destination"
                )
            ),

            "last_scanned_location": (
                shipment.last_scanned_location
            ),

            "last_scanned_at": (
                shipment.last_scanned_at
            ),

            # ----------------------------------------------------
            # COMPLETE SCAN HISTORY
            # ----------------------------------------------------

            "scans": scans,
        },
    }