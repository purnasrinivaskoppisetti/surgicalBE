from uuid import UUID

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload

from app.models.models import (
    Order,
    OrderItem,
    Product,
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

                # ------------------------------------------------
                # USER
                # ------------------------------------------------

                joinedload(
                    Order.user
                ),

                # ------------------------------------------------
                # ORDER ITEMS → PRODUCT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.images
                ),

                # ------------------------------------------------
                # ORDER ITEMS → VARIANT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.variant
                ),

                # ------------------------------------------------
                # ADDRESS
                # ------------------------------------------------

                joinedload(
                    Order.address
                ),

                # ------------------------------------------------
                # PAYMENTS
                # ------------------------------------------------

                joinedload(
                    Order.payments
                ),

                # ------------------------------------------------
                # SHIPMENTS
                # ------------------------------------------------

                joinedload(
                    Order.shipments
                ),

                # ------------------------------------------------
                # COUPON
                # ------------------------------------------------

                joinedload(
                    Order.coupon
                ),

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

        return (
            result
            .scalars()
            .first()
        )


    # ============================================================
    # GET PAYMENT WITH DATABASE LOCK
    # ============================================================

    @staticmethod
    async def get_payment_for_update(
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

            .with_for_update()
        )

        return (
            result
            .scalars()
            .first()
        )


    # ============================================================
    # SAVE
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

        await db.refresh(
            obj
        )