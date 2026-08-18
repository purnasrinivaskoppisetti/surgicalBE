# app/api/routes/shipping_routes.py

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Address
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
        3. Gets customer's saved order address
        4. Finds shipment
        5. Gets AWB
        6. Calls Blue Dart
        7. Updates local shipment
        8. Saves scan history
        9. Returns live tracking data
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
    # 3. GET CUSTOMER SAVED ADDRESS
    # ============================================================
    #
    # IMPORTANT:
    # Do NOT use Blue Dart's Destination here.
    #
    # Blue Dart may return:
    #
    #     Destination = GUNTUR
    #
    # even when the customer's actual saved address is:
    #
    #     Narsapur - 534281
    #
    # The order has address_id, so use the address linked
    # to this specific order.
    # ============================================================

    customer_address = None

    if order.address_id:

        address_result = await db.execute(
            select(Address).where(
                Address.id == order.address_id
            )
        )

        customer_address = (
            address_result.scalar_one_or_none()
        )

    # ============================================================
    # 4. BUILD CUSTOMER DESTINATION
    # ============================================================

    destination = None

    if customer_address:

        destination = {
            "full_name": (
                customer_address.full_name
            ),

            "address_line1": (
                customer_address.address_line1
            ),

            "address_line2": (
                customer_address.address_line2
            ),

            "landmark": (
                customer_address.landmark
            ),

            "city": (
                customer_address.city
            ),

            "state": (
                customer_address.state
            ),

            "pincode": (
                customer_address.pincode
            ),

            "country": (
                customer_address.country
            ),

            "phone": (
                customer_address.phone
            ),
        }

    # ============================================================
    # 5. FIND SHIPMENT
    # ============================================================

    shipment = (
        await ShipmentRepository.get_by_order_id(
            db,
            order_id
        )
    )

    # ============================================================
    # 6. WAYBILL NOT GENERATED
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

                "destination": destination,

                "scans": [],
            },
        }

    # ============================================================
    # 7. GET AWB
    # ============================================================

    awb_number = (
        shipment.tracking_number.strip()
    )

    # ============================================================
    # 8. CALL BLUE DART
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
    # 9. UPDATE LOCAL SHIPMENT
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

        shipment.status = (
            tracking_status
        )

    # ============================================================
    # 10. SAVE LATEST SCAN
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
    # 11. COMMIT LOCAL TRACKING DATA
    # ============================================================

    try:

        await db.commit()

        await db.refresh(
            shipment
        )

    except Exception as exc:

        await db.rollback()

        # Blue Dart tracking was successful,
        # but local database update failed.
        #
        # We still return the live tracking data.

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

                "shipment_id": (
                    str(shipment.id)
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

                # Blue Dart origin
                "origin": (
                    tracking_data.get(
                        "origin"
                    )
                ),

                # CUSTOMER SAVED ADDRESS
                "destination": destination,

                "scans": scans,

                "database_sync_error": (
                    str(exc)
                ),
            },
        }

    # ============================================================
    # 12. ORDER STATUS
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
    # 13. FINAL RESPONSE
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

            "shipment_id": (
                str(shipment.id)
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

            # Blue Dart origin
            "origin": (
                tracking_data.get(
                    "origin"
                )
            ),

            # IMPORTANT:
            # Use customer's saved order address,
            # NOT Blue Dart's destination.
            "destination": destination,

            # ----------------------------------------------------
            # LAST SCAN
            # ----------------------------------------------------

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