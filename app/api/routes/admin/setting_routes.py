from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import (
    AsyncSession
)

from app.core.database import get_db

from app.services.admin.setting_service import (
    SettingService
)

from app.schemas.admin.setting_schema import (
    UpdateGeneralSettingsRequest,
    UpdateStoreSettingsRequest,
    UpdateDeliverySettingsRequest
)

router = APIRouter(
    prefix="/admin/settings",
    tags=["Admin Settings"]
)


@router.get("/general")
async def get_general_settings(
    db: AsyncSession = Depends(get_db)
):
    return {
        "success": True,
        "data": await SettingService.get_general_settings(
            db
        )
    }


@router.patch("/general")
async def update_general_settings(
    request: UpdateGeneralSettingsRequest,
    db: AsyncSession = Depends(get_db)
):
    await SettingService.update_general_settings(
        db,
        request
    )

    return {
        "success": True,
        "message": "Settings updated"
    }


@router.get("/store")
async def get_store_settings(
    db: AsyncSession = Depends(get_db)
):
    return {
        "success": True,
        "data": await SettingService.get_store_settings(
            db
        )
    }


@router.patch("/store")
async def update_store_settings(
    request: UpdateStoreSettingsRequest,
    db: AsyncSession = Depends(get_db)
):
    await SettingService.update_store_settings(
        db,
        request
    )

    return {
        "success": True,
        "message": "Settings updated"
    }


@router.get("/delivery")
async def get_delivery_settings(
    db: AsyncSession = Depends(get_db)
):
    return {
        "success": True,
        "data": await SettingService.get_delivery_settings(
            db
        )
    }


@router.patch("/delivery")
async def update_delivery_settings(
    request: UpdateDeliverySettingsRequest,
    db: AsyncSession = Depends(get_db)
):
    await SettingService.update_delivery_settings(
        db,
        request
    )

    return {
        "success": True,
        "message": "Settings updated"
    }