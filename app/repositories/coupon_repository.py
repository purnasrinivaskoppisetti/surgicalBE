from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Coupon


class CouponRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        coupon: Coupon
    ):
        db.add(coupon)

        await db.commit()

        await db.refresh(coupon)

        return coupon

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        coupon_id: UUID
    ):
        result = await db.execute(
            select(Coupon)
            .where(
                Coupon.id == coupon_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(
        db: AsyncSession,
        code: str
    ):
        result = await db.execute(
            select(Coupon)
            .where(
                Coupon.code == code
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession
    ):
        result = await db.execute(
            select(Coupon)
            .order_by(
                Coupon.created_at.desc()
            )
        )

        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession,
        coupon
    ):
        await db.commit()

        await db.refresh(coupon)

        return coupon

    @staticmethod
    async def delete(
        db: AsyncSession,
        coupon
    ):
        await db.delete(coupon)

        await db.commit()