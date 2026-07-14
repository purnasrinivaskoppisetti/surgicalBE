from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.banner_repository import BannerRepository


class BannerService:

    @staticmethod
    async def get_banners(db: AsyncSession):
        try:
            banners = await BannerRepository.get_banners(db)

            # Return empty list if no banners are available
            return banners

        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while fetching banners."
            ) from e

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while fetching banners."
            ) from e