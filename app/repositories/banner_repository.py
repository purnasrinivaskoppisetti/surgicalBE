from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Banner


class BannerRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        banner: Banner
    ) -> Banner:

        db.add(banner)

        await db.commit()
        await db.refresh(banner)

        return banner

    @staticmethod
    async def get_all(
        db: AsyncSession
    ) -> list[Banner]:

        result = await db.execute(
            select(Banner)
            .where(
                Banner.is_deleted == False
            )
            .order_by(
                Banner.sort_order.asc()
            )
        )

        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        banner_id: UUID
    ) -> Banner | None:

        result = await db.execute(
            select(Banner)
            .where(
                Banner.id == banner_id,
                Banner.is_deleted == False
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        banner: Banner
    ) -> Banner:

        await db.commit()
        await db.refresh(banner)

        return banner

    @staticmethod
    async def delete(
        db: AsyncSession,
        banner: Banner
    ) -> bool:

        banner.is_deleted = True

        await db.commit()

        return True
    @staticmethod
    async def get_banners(db: AsyncSession):

        result = await db.execute(
            select(Banner)
            .where(
                Banner.is_active == True,
                Banner.is_deleted == False
            )
            .order_by(Banner.sort_order.asc())
        )

        return result.scalars().all()