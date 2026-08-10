# app/api/routes/admin/order_routes.py

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin

from app.services.admin.order_service import (
    OrderService,
)

from app.schemas.admin.order_schema import (
    UpdateOrderStatusRequest,
    UpdatePaymentStatusRequest,
    CancelOrderRequest,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin Orders"],
    dependencies=[
        Depends(get_current_admin)
    ],
)


# ============================================================
# GET ADMIN ORDERS
#
# GET /api/v1/admin/orders
#
# Returns:
# - order status
# - payment status
# - AWB / waybill
# - courier
# - shipment status
# - current location
# - last scanned time
# ============================================================

@router.get("")
async def get_orders(
    page: int = Query(
        1,
        ge=1,
        description="Page number",
    ),

    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of orders per page",
    ),

    search: str | None = Query(
        None,
        description="Search order number/customer name/phone",
    ),

    status: str | None = Query(
        None,
        description="Filter by order status",
    ),

    payment_status: str | None = Query(
        None,
        description="Filter by payment status",
    ),

    db: AsyncSession = Depends(
        get_db
    ),
):

    data = await OrderService.get_orders(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        payment_status=payment_status,
    )

    return {
        "success": True,
        "status_code": 200,
        "message": "Orders fetched successfully",
        "data": data,
    }


# ============================================================
# SYNC BLUE DART TRACKING
#
# IMPORTANT:
# Keep this BEFORE /{order_id}
#
# GET /api/v1/admin/orders/{order_id}/tracking
# ============================================================

@router.get(
    "/{order_id}/tracking"
)
async def sync_tracking(
    order_id: UUID,

    db: AsyncSession = Depends(
        get_db
    ),
):

    return await OrderService.sync_shipment_status(
        db=db,
        order_id=order_id,
    )


# ============================================================
# GET SINGLE ADMIN ORDER
#
# GET /api/v1/admin/orders/{order_id}
#
# Returns:
#
# ORDER
# ├── order_status
# ├── payment_status
#
# CUSTOMER
#
# ADDRESS
#
# PRODUCTS
#
# PAYMENTS
#
# SHIPMENT
# ├── courier
# ├── AWB
# ├── waybill_generated
# ├── waybill_status
# ├── status_code
# ├── current_location
# ├── last_scanned_at
# ├── estimated_delivery
# └── tracking_history[]
#
# ============================================================

@router.get(
    "/{order_id}"
)
async def get_order(
    order_id: UUID,

    db: AsyncSession = Depends(
        get_db
    ),
):

    data = await OrderService.get_order(
        db=db,
        order_id=order_id,
    )

    return {
        "success": True,
        "status_code": 200,
        "message": "Order fetched successfully",
        "data": data,
    }


# ============================================================
# UPDATE ORDER STATUS
#
# PATCH /api/v1/admin/orders/{order_id}/status
# ============================================================

@router.patch(
    "/{order_id}/status"
)
async def update_status(
    order_id: UUID,

    request: UpdateOrderStatusRequest,

    db: AsyncSession = Depends(
        get_db
    ),
):

    data = await OrderService.update_status(
        db=db,
        order_id=order_id,
        status=request.status,
    )

    return {
        "success": True,
        "status_code": 200,
        "message": "Order status updated",
        "data": data,
    }


# ============================================================
# UPDATE PAYMENT STATUS
#
# PATCH /api/v1/admin/orders/{order_id}/payment-status
# ============================================================

@router.patch(
    "/{order_id}/payment-status"
)
async def update_payment_status(
    order_id: UUID,

    request: UpdatePaymentStatusRequest,

    db: AsyncSession = Depends(
        get_db
    ),
):

    data = await OrderService.update_payment_status(
        db=db,
        order_id=order_id,
        payment_status=request.payment_status,
    )

    return {
        "success": True,
        "status_code": 200,
        "message": "Payment status updated",
        "data": data,
    }


# ============================================================
# CANCEL ORDER
#
# PATCH /api/v1/admin/orders/{order_id}/cancel
# ============================================================

@router.patch(
    "/{order_id}/cancel"
)
async def cancel_order(
    order_id: UUID,

    request: CancelOrderRequest,

    db: AsyncSession = Depends(
        get_db
    ),
):

    data = await OrderService.cancel_order(
        db=db,
        order_id=order_id,
        reason=request.reason,
    )

    return {
        "success": True,
        "status_code": 200,
        "message": "Order cancelled",
        "data": data,
    }