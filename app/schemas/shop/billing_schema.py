# app/schemas/shop/billing_schema.py

from uuid import UUID
from decimal import Decimal

from pydantic import (
    BaseModel,
    Field,
)


# ============================================================
# CREATE PAYMENT
# ============================================================

class CreatePaymentRequest(BaseModel):

    order_id: UUID


# ============================================================
# CREATE PAYMENT RESPONSE
# ============================================================

class CreatePaymentResponse(BaseModel):

    order_id: UUID

    razorpay_order_id: str

    amount: int

    currency: str

    razorpay_key: str


# ============================================================
# VERIFY PAYMENT
# ============================================================

class VerifyPaymentRequest(BaseModel):

    order_id: UUID

    razorpay_order_id: str = Field(
        min_length=1
    )

    razorpay_payment_id: str = Field(
        min_length=1
    )

    razorpay_signature: str = Field(
        min_length=1
    )


# ============================================================
# VERIFY PAYMENT RESPONSE
# ============================================================

class VerifyPaymentResponse(BaseModel):

    success: bool

    message: str


# ============================================================
# PAYMENT RESPONSE
# ============================================================

class PaymentResponse(BaseModel):

    id: UUID

    amount: Decimal

    status: str

    gateway_order_id: str | None = None

    gateway_transaction_id: str | None = None