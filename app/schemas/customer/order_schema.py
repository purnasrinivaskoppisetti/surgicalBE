from uuid import UUID

from pydantic import BaseModel, Field

from app.models.models import PaymentMethod


# ============================================================
# CREATE ORDER
# ============================================================

class CreateOrderRequest(BaseModel):

    address_id: UUID

    payment_method: PaymentMethod

    coupon_code: str | None = None


# ============================================================
# PAYMENT SUCCESS
# ============================================================

class PaymentSuccessRequest(BaseModel):

    order_id: UUID

    transaction_id: str = Field(
        min_length=1
    )


# ============================================================
# CANCEL ORDER
# ============================================================

class CancelOrderRequest(BaseModel):

    reason: str = Field(
        min_length=1,
        max_length=500
    )