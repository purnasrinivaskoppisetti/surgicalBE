from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.models import (
    WishlistItem,
    Product
)


class WishlistRepository:

    @staticmethod
    async def get_by_user_and_product(
        db: AsyncSession,
        user_id: UUID,
        product_id: UUID
    ):

        result = await db.execute(
            select(WishlistItem)
            .where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        wishlist_item: WishlistItem
    ):

        db.add(wishlist_item)

        await db.commit()

        await db.refresh(
            wishlist_item
        )

        return wishlist_item

    @staticmethod
    async def get_user_wishlist(
        db: AsyncSession,
        user_id: UUID,
        page: int,
        page_size: int
    ):

        # ========================================================
        # TOTAL COUNT
        # ========================================================

        count_result = await db.execute(
            select(
                func.count(WishlistItem.id)
            )
            .where(
                WishlistItem.user_id == user_id
            )
        )

        total_records = (
            count_result.scalar() or 0
        )

        # ========================================================
        # GET WISHLIST
        # ========================================================

        result = await db.execute(

            select(WishlistItem)

            .options(

                # Product
                joinedload(
                    WishlistItem.product
                ),

                # Product Images
                joinedload(
                    WishlistItem.product
                ).joinedload(
                    Product.images
                ),

                # Product Category
                joinedload(
                    WishlistItem.product
                ).joinedload(
                    Product.category
                ),

                # Product Variants
                joinedload(
                    WishlistItem.product
                ).joinedload(
                    Product.variants
                )
            )

            .where(
                WishlistItem.user_id == user_id
            )

            .order_by(
                WishlistItem.created_at.desc()
            )

            .offset(
                (page - 1) * page_size
            )

            .limit(
                page_size
            )
        )

        # joinedload on multiple collections
        # can create duplicate rows.
        items = (
            result
            .unique()
            .scalars()
            .all()
        )

        return (
            items,
            total_records
        )

    @staticmethod
    async def delete(
        db: AsyncSession,
        wishlist_item: WishlistItem
    ):

        await db.delete(
            wishlist_item
        )

        await db.commit()