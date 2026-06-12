from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.schemas.shop.billing_schema import (
    CreatePaymentRequest,
    VerifyPaymentRequest
)

from app.services.shop.billing_service import (
    BillingService
)

router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


@router.post("/create-payment")
async def create_payment(
    payload: CreatePaymentRequest,
    db: AsyncSession = Depends(get_db)
):

    return await BillingService.create_payment(
        db,
        payload.order_id
    )


@router.post("/verify-payment")
async def verify_payment(
    payload: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db)
):

    return await BillingService.verify_payment(
        db,
        payload
    )