from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.core.storage import local_storage

from app.schemas.admin.common_schema import ApiResponse

from app.services.admin.banner_service import BannerService


router = APIRouter(
    prefix="/admin/settings",
    tags=["Admin Settings"]
)


@router.post(
    "/banner",
    response_model=ApiResponse
)
async def create_banner(
    title: str = Form(...),
    subtitle: str = Form(None),
    redirect_url: str = Form(None),
    sort_order: int = Form(0),
    is_active: bool = Form(True),
    image: UploadFile = File(...),
    mobile_image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    image_url = await local_storage.upload_banner_image(
        image
    )

    mobile_image_url = None

    if mobile_image:
        mobile_image_url = await local_storage.upload_banner_image(
            mobile_image
        )

    banner = await BannerService.create_banner(
        db=db,
        image_url=image_url,
        mobile_image_url=mobile_image_url,
        request=type(
            "",
            (),
            {
                "title": title,
                "subtitle": subtitle,
                "redirect_url": redirect_url,
                "sort_order": sort_order,
                "is_active": is_active
            }
        )
    )

    return ApiResponse(
        success=True,
        status_code=201,
        message="Banner created successfully",
        data=banner
    )


@router.get(
    "/banner",
    response_model=ApiResponse
)
async def get_banners(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    banners = await BannerService.get_all_banners(
        db
    )

    return ApiResponse(
        success=True,
        status_code=200,
        message="Banner list",
        data=banners
    )


@router.get(
    "/banner/{banner_id}",
    response_model=ApiResponse
)
async def get_banner(
    banner_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    banner = await BannerService.get_banner(
        db,
        banner_id
    )

    return ApiResponse(
        success=True,
        status_code=200,
        message="Banner details",
        data=banner
    )


@router.patch(
    "/banner/{banner_id}",
    response_model=ApiResponse
)
async def update_banner(
    banner_id: UUID,
    title: str = Form(...),
    subtitle: str = Form(None),
    redirect_url: str = Form(None),
    sort_order: int = Form(0),
    is_active: bool = Form(True),
    image: UploadFile = File(None),
    mobile_image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    image_url = None
    mobile_image_url = None

    if image:
        image_url = await local_storage.upload_banner_image(
            image
        )

    if mobile_image:
        mobile_image_url = await local_storage.upload_banner_image(
            mobile_image
        )

    banner = await BannerService.update_banner(
        db=db,
        banner_id=banner_id,
        request=type(
            "",
            (),
            {
                "title": title,
                "subtitle": subtitle,
                "redirect_url": redirect_url,
                "sort_order": sort_order,
                "is_active": is_active
            }
        ),
        image_url=image_url,
        mobile_image_url=mobile_image_url
    )

    return ApiResponse(
        success=True,
        status_code=200,
        message="Banner updated successfully",
        data=banner
    )


@router.delete(
    "/banner/{banner_id}",
    response_model=ApiResponse
)
async def delete_banner(
    banner_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):

    await BannerService.delete_banner(
        db,
        banner_id
    )

    return ApiResponse(
        success=True,
        status_code=200,
        message="Banner deleted successfully",
        data=None
    )