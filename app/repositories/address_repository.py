from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Address


class AddressRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        address: Address
    ):

        db.add(address)

        await db.commit()

        await db.refresh(address)

        return address

    @staticmethod
    async def get_user_addresses(
        db: AsyncSession,
        user_id: UUID
    ):

        result = await db.execute(
            select(Address)
            .where(
                Address.user_id == user_id
            )
            .order_by(
                Address.created_at.desc()
            )
        )

        return result.scalars().all()