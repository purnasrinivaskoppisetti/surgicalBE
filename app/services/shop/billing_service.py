from datetime import datetime

from fastapi import HTTPException
from razorpay.errors import SignatureVerificationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.razorpay import client

from app.models.models import (
    PaymentStatus,
    OrderStatus
)

from app.repositories.bill_repository import (
    BillRepository
)


class BillingService:

    @staticmethod
    async def create_payment(
        db: AsyncSession,
        user_id,
        order_id
    ):

        order = await BillRepository.get_order(
            db,
            order_id
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        if str(order.user_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        payment = await BillRepository.get_payment_by_order(
            db,
            order.id
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment not found"
            )

        razorpay_order = client.order.create(
            {
                "amount": int(float(order.total_amount) * 100),
                "currency": "INR",
                "receipt": order.order_number
            }
        )

        payment.gateway_order_id = razorpay_order["id"]

        await db.commit()

        return {
            "success": True,
            "status_code": 200,
            "message": "Payment order created successfully",
            "data": {
                "order_id": str(order.id),
                "razorpay_order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"]
            }
        }

    @staticmethod
    async def verify_payment(
        db: AsyncSession,
        user_id,
        payload
    ):

        try:

            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id":
                    payload.razorpay_order_id,

                    "razorpay_payment_id":
                    payload.razorpay_payment_id,

                    "razorpay_signature":
                    payload.razorpay_signature
                }
            )

        except SignatureVerificationError:

            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature"
            )

        order = await BillRepository.get_order(
            db,
            payload.order_id
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        if str(order.user_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

        payment = await BillRepository.get_payment_by_order(
            db,
            payload.order_id
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment not found"
            )

        payment.status = PaymentStatus.PAID

        payment.gateway_transaction_id = (
            payload.razorpay_payment_id
        )

        payment.payment_response_data = {
            "razorpay_payment_id":
            payload.razorpay_payment_id,

            "razorpay_order_id":
            payload.razorpay_order_id
        }

        payment.paid_at = datetime.utcnow()

        order.payment_status = PaymentStatus.PAID
        order.status = OrderStatus.CONFIRMED

        await db.commit()

        return {
            "success": True,
            "status_code": 200,
            "message": "Payment successful"
        }