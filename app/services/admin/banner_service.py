from uuid import UUID

from app.models.models import Banner
from app.repositories.banner_repository import BannerRepository


class BannerService:

    @staticmethod
    async def create_banner(
        db,
        image_url: str,
        mobile_image_url: str | None,
        request
    ):

        banner = Banner(
            title=request.title,
            subtitle=request.subtitle,
            image_url=image_url,
            mobile_image_url=mobile_image_url,
            redirect_url=request.redirect_url,
            sort_order=request.sort_order,
            is_active=request.is_active
        )

        return await BannerRepository.create(
            db,
            banner
        )

    @staticmethod
    async def get_all_banners(
        db
    ):
        return await BannerRepository.get_all(db)

    @staticmethod
    async def get_banner(
        db,
        banner_id: UUID
    ):
        return await BannerRepository.get_by_id(
            db,
            banner_id
        )

    @staticmethod
    async def update_banner(
        db,
        banner_id: UUID,
        request,
        image_url: str | None = None,
        mobile_image_url: str | None = None
    ):

        banner = await BannerRepository.get_by_id(
            db,
            banner_id
        )

        if not banner:
            return None

        banner.title = request.title
        banner.subtitle = request.subtitle
        banner.redirect_url = request.redirect_url
        banner.sort_order = request.sort_order
        banner.is_active = request.is_active

        if image_url is not None:
            banner.image_url = image_url

        if mobile_image_url is not None:
            banner.mobile_image_url = mobile_image_url

        return await BannerRepository.update(
            db,
            banner
        )

    @staticmethod
    async def delete_banner(
        db,
        banner_id: UUID
    ):

        banner = await BannerRepository.get_by_id(
            db,
            banner_id
        )

        if not banner:
            return False

        return await BannerRepository.delete(
            db,
            banner
        )