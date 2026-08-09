# app/repositories/bill_repository.py

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.models import (
    Order,
    Payment,
)


class BillRepository:

    # ============================================================
    # GET ORDER
    # ============================================================

    @staticmethod
    async def get_order(
        db: AsyncSession,
        order_id: UUID,
    ):
        result = await db.execute(

            select(Order)

            .options(
                joinedload(Order.user),
                joinedload(Order.items),
                joinedload(Order.address),
                joinedload(Order.payments),
                joinedload(Order.shipments),
            )

            .where(
                Order.id == order_id
            )
        )

        return (
            result
            .unique()
            .scalar_one_or_none()
        )

    # ============================================================
    # GET PAYMENT
    # ============================================================

    @staticmethod
    async def get_payment_by_order(
        db: AsyncSession,
        order_id: UUID,
    ):
        result = await db.execute(

            select(Payment)

            .where(
                Payment.order_id == order_id
            )

            .order_by(
                Payment.created_at.desc()
            )
        )

        return result.scalars().first()

    # ============================================================
    # COMMIT
    # ============================================================

    @staticmethod
    async def save(
        db: AsyncSession,
    ):
        await db.commit()

    # ============================================================
    # REFRESH
    # ============================================================

    @staticmethod
    async def refresh(
        db: AsyncSession,
        obj,
    ):
        await db.refresh(obj)