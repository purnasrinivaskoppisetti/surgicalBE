from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.store.banner_schema import BannerResponse
from app.services.store.banner_service import BannerService

router = APIRouter(
    prefix="/banners",
    tags=["User Banners"]
)


@router.get(
    "",
    response_model=list[BannerResponse]
)
async def get_banners(
    db: AsyncSession = Depends(get_db)
):

    return await BannerService.get_banners(db)