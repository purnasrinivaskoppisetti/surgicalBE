from uuid import UUID

from pydantic import BaseModel

from app.models.models import PaymentMethod


class CreateOrderRequest(BaseModel):

    address_id: UUID

    payment_method: PaymentMethod

    coupon_code: str | None = None


class PaymentSuccessRequest(BaseModel):
    address_id: UUID
    transaction_id: str
    coupon_code: str | None = None

class CancelOrderRequest(BaseModel):

    reason: str