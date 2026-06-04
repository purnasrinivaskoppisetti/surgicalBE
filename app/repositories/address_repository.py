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
            .where(Address.user_id == user_id)
            .order_by(Address.created_at.desc())
        )

        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        address_id: UUID,
        user_id: UUID
    ):
        result = await db.execute(
            select(Address)
            .where(
                Address.id == address_id,
                Address.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        address: Address
    ):
        await db.commit()
        await db.refresh(address)
        return address

    @staticmethod
    async def delete(
        db: AsyncSession,
        address: Address
    ):
        await db.delete(address)
        await db.commit()