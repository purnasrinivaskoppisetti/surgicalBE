from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_admin

from app.models.models import (
    Order,
    OrderItem,
    Product,
    OrderStatus,
    PaymentStatus,
    Shipment,
    StoreSetting,
)

from app.services.bluedart_service import (
    BlueDartService,
)


router = APIRouter(
    prefix="/admin/shipping",
    tags=["Admin Shipping"],
)


@router.post(
    "/generate-waybill/{order_id}"
)
async def generate_order_waybill(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Generate Blue Dart Waybill for an order.

    Admin sends only order_id.

    Backend automatically loads:
        - customer
        - delivery address
        - payment
        - order items
        - products
        - categories
        - existing shipments
        - store settings

    Then:
        DB
        ↓
        calculate package
        ↓
        Blue Dart
        ↓
        AWB
        ↓
        save shipment
    """

    # ============================================================
    # 1. LOAD COMPLETE ORDER
    # ============================================================

    order_stmt = (
        select(Order)
        .where(
            Order.id == order_id
        )
        .options(

            # Customer
            selectinload(
                Order.user
            ),

            # Delivery address
            selectinload(
                Order.address
            ),

            # Payments
            selectinload(
                Order.payments
            ),

            # Existing shipments
            selectinload(
                Order.shipments
            ),

            # Order items
            # OrderItem.product
            # Product.category
            selectinload(
                Order.items
            )
            .selectinload(
                OrderItem.product
            )
            .selectinload(
                Product.category
            ),
        )
    )

    result = await db.execute(
        order_stmt
    )

    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Order {order_id} "
                "not found."
            ),
        )

    # ============================================================
    # 2. CHECK ADDRESS
    # ============================================================

    if not order.address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cannot generate Waybill: "
                "delivery address is missing."
            ),
        )

    # ============================================================
    # 3. CHECK ORDER ITEMS
    # ============================================================

    if not order.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cannot generate Waybill: "
                "order contains no products."
            ),
        )

    # Make sure every item has product data
    for item in order.items:

        if not item.product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Product information is missing "
                    f"for order item {item.id}."
                ),
            )

    # ============================================================
    # 4. PAYMENT CHECK
    # ============================================================

    is_cod = False

    if order.payments:

        latest_payment = max(
            order.payments,
            key=lambda payment: (
                payment.created_at
                if payment.created_at
                else order.created_at
            ),
        )

        payment_method = str(
            latest_payment.payment_method
        ).lower()

        is_cod = (
            payment_method == "cod"
            or payment_method.endswith(
                ".cod"
            )
        )

    # Online payment must be paid
    if (
        not is_cod
        and order.payment_status
        != PaymentStatus.PAID
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cannot generate Waybill: "
                "Online payment is incomplete "
                "or pending."
            ),
        )

    # ============================================================
    # 5. PREVENT DUPLICATE WAYBILL
    # ============================================================

    existing_shipment = None

    for shipment in order.shipments:

        if shipment.tracking_number:
            existing_shipment = shipment
            break

    if existing_shipment:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": (
                    "Waybill already generated "
                    "for this order."
                ),
                "order_id": str(
                    order.id
                ),
                "awb_number": (
                    existing_shipment.tracking_number
                ),
            },
        )

    # ============================================================
    # 6. GET STORE SETTINGS
    # ============================================================

    store_stmt = (
        select(StoreSetting)
        .order_by(
            StoreSetting.created_at.asc()
        )
        .limit(1)
    )

    store_result = await db.execute(
        store_stmt
    )

    store_setting = (
        store_result.scalar_one_or_none()
    )

    # ============================================================
    # 7. CALCULATE PACKAGE
    # ============================================================

    try:

        package_details = (
            BlueDartService.calculate_package_details(
                order
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Shipment calculation failed: "
                f"{str(exc)}"
            ),
        )

    # ============================================================
    # 8. CALL BLUE DART
    # ============================================================

    try:

        waybill_response = (
            await BlueDartService.generate_waybill(
                order=order,
                address=order.address,
                store_setting=store_setting,
            )
        )

    except HTTPException:

        await db.rollback()
        raise

    except Exception as exc:

        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Blue Dart Waybill Generation Failed: "
                f"{str(exc)}"
            ),
        )

    # ============================================================
    # 9. GET AWB
    # ============================================================

    awb_number = (
        waybill_response.get(
            "awb_number"
        )
    )

    if not awb_number:

        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Blue Dart did not return "
                "an AWB number."
            ),
        )

    # ============================================================
    # 10. CREATE SHIPMENT
    # ============================================================

    shipment = Shipment(

        order_id=order.id,

        courier_name="Blue Dart",

        tracking_number=awb_number,

        # Blue Dart response
        pickup_token_number=(
            waybill_response.get(
                "pickup_token_number"
            )
        ),

        cluster_code=(
            waybill_response.get(
                "cluster_code"
            )
        ),

        origin_area=(
            settings.BLUEDART_ORIGIN_AREA
        ),

        destination_area=(
            waybill_response.get(
                "destination_area"
            )
        ),

        destination_location=(
            waybill_response.get(
                "destination_location"
            )
        ),

        mps_details=(
            waybill_response.get(
                "mps_details"
            )
        ),

        # Package details
        actual_weight=(
            waybill_response.get(
                "actual_weight"
            )
        ),

        length=(
            waybill_response.get(
                "length"
            )
        ),

        breadth=(
            waybill_response.get(
                "breadth"
            )
        ),

        height=(
            waybill_response.get(
                "height"
            )
        ),

        piece_count=(
            waybill_response.get(
                "piece_count",
                1,
            )
        ),

        # Blue Dart product
        product_code=(
            waybill_response.get(
                "product_code"
            )
        ),

        sub_product_code=(
            waybill_response.get(
                "sub_product_code"
            )
        ),

        pack_type=(
            waybill_response.get(
                "pack_type",
                "L",
            )
        ),

        status=(
            "PICKUP HAS BEEN_REGISTERED"
        ),
    )

    db.add(shipment)

    # ============================================================
    # 11. UPDATE ORDER
    # ============================================================

    order.status = OrderStatus.PACKED

    # ============================================================
    # 12. SAVE
    # ============================================================

    try:

        await db.commit()

        await db.refresh(
            shipment
        )

        await db.refresh(
            order
        )

    except Exception as exc:

        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to save shipment: "
                f"{str(exc)}"
            ),
        )

    # ============================================================
    # 13. RESPONSE
    # ============================================================

    return {
        "success": True,

        "message": (
            "Waybill generated successfully "
            "and shipment saved."
        ),

        "data": {

            "order_id": str(
                order.id
            ),

            "order_number": (
                order.order_number
            ),

            "order_status": (
                order.status.value
            ),

            "payment_type": (
                "COD"
                if is_cod
                else "PREPAID"
            ),

            "shipment_id": str(
                shipment.id
            ),

            "courier": (
                shipment.courier_name
            ),

            "awb_number": (
                shipment.tracking_number
            ),

            "pickup_token_number": (
                shipment.pickup_token_number
            ),

            "cluster_code": (
                shipment.cluster_code
            ),

            "destination_area": (
                shipment.destination_area
            ),

            "destination_location": (
                shipment.destination_location
            ),

            "actual_weight": (
                float(
                    shipment.actual_weight
                )
                if shipment.actual_weight
                is not None
                else None
            ),

            "length": (
                float(
                    shipment.length
                )
                if shipment.length
                is not None
                else None
            ),

            "breadth": (
                float(
                    shipment.breadth
                )
                if shipment.breadth
                is not None
                else None
            ),

            "height": (
                float(
                    shipment.height
                )
                if shipment.height
                is not None
                else None
            ),

            "piece_count": (
                shipment.piece_count
            ),

            "product_code": (
                shipment.product_code
            ),

            "sub_product_code": (
                shipment.sub_product_code
            ),

            "pack_type": (
                shipment.pack_type
            ),
        },
    }