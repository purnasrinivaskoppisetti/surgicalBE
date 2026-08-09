# app/api/routes/admin/order_routes.py

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.database import (
    get_db,
)

from app.core.dependencies import (
    get_current_admin,
)

from app.services.admin.order_service import (
    OrderService,
)

from app.schemas.admin.order_schema import (
    UpdateOrderStatusRequest,
    UpdatePaymentStatusRequest,
    CancelOrderRequest,
)


router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin Orders"],
    dependencies=[
        Depends(get_current_admin)
    ],
)


# ============================================================
# GET ADMIN ORDERS
# ============================================================

@router.get("")
async def get_orders(
    page: int = Query(
        1,
        ge=1
    ),

    page_size: int = Query(
        20,
        ge=1,
        le=100
    ),

    search: str | None = None,

    status: str | None = None,

    payment_status: str | None = None,

    db: AsyncSession = Depends(
        get_db
    ),
):

    return {

        "success": True,

        "status_code": 200,

        "data":
            await OrderService.get_orders(
                db,
                page,
                page_size,
                search,
                status,
                payment_status,
            ),
    }


# ============================================================
# GET SINGLE ADMIN ORDER
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

    return {

        "success": True,

        "status_code": 200,

        "data":
            await OrderService.get_order(
                db,
                order_id,
            ),
    }


# ============================================================
# SYNC BLUE DART TRACKING
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

    return await (
        OrderService
        .sync_shipment_status(
            db,
            order_id,
        )
    )


# ============================================================
# UPDATE ORDER STATUS
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

    return {

        "success": True,

        "status_code": 200,

        "message":
            "Order status updated",

        "data":
            await OrderService.update_status(
                db,
                order_id,
                request.status,
            ),
    }


# ============================================================
# UPDATE PAYMENT STATUS
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

    return {

        "success": True,

        "status_code": 200,

        "message":
            "Payment updated",

        "data":
            await OrderService.update_payment_status(
                db,
                order_id,
                request.payment_status,
            ),
    }


# ============================================================
# CANCEL ORDER
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

    return {

        "success": True,

        "status_code": 200,

        "message":
            "Order cancelled",

        "data":
            await OrderService.cancel_order(
                db,
                order_id,
                request.reason,
            ),
    }