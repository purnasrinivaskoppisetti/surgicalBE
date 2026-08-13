from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.models import (
    CartItem,
    Product,
)


class CartRepository:

    # ============================================================
    # GET CART ITEM BY USER + PRODUCT
    # ============================================================

    @staticmethod
    async def get_by_user_and_product(
        db: AsyncSession,
        user_id: UUID,
        product_id: UUID,
    ):
        """
        Get a cart item using user_id + product_id.

        NOTE:
        If your cart supports multiple variants of the same product,
        prefer get_by_user_and_variant() below.
        """

        result = await db.execute(
            select(CartItem)
            .where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # GET CART ITEM BY USER + PRODUCT + VARIANT
    # ============================================================

    @staticmethod
    async def get_by_user_and_variant(
        db: AsyncSession,
        user_id: UUID,
        product_id: UUID,
        variant_id: UUID,
    ):
        """
        Get a specific product variant from the user's cart.

        Example:

            T-Shirt / Red / M

        is different from:

            T-Shirt / Red / L
        """

        result = await db.execute(
            select(CartItem)
            .where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
                CartItem.variant_id == variant_id,
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # CREATE CART ITEM
    # ============================================================

    @staticmethod
    async def create(
        db: AsyncSession,
        cart_item: CartItem,
    ):
        db.add(cart_item)

        await db.commit()

        await db.refresh(cart_item)

        return cart_item

    # ============================================================
    # UPDATE CART ITEM
    # ============================================================

    @staticmethod
    async def update(
        db: AsyncSession,
        cart_item: CartItem,
    ):
        await db.commit()

        await db.refresh(cart_item)

        return cart_item

    # ============================================================
    # GET PAGINATED CART ITEMS
    # ============================================================

    @staticmethod
    async def get_cart_items(
        db: AsyncSession,
        user_id: UUID,
        page: int,
        page_size: int,
    ):
        # --------------------------------------------------------
        # COUNT CART ITEMS
        # --------------------------------------------------------

        count_result = await db.execute(
            select(
                func.count(CartItem.id)
            )
            .where(
                CartItem.user_id == user_id
            )
        )

        total_records = (
            count_result.scalar() or 0
        )

        # --------------------------------------------------------
        # GET CART ITEMS
        # --------------------------------------------------------

        result = await db.execute(
            select(CartItem)
            .options(

                # =================================================
                # PRODUCT
                # =================================================

                joinedload(
                    CartItem.product
                )
                .joinedload(
                    Product.images
                ),

                joinedload(
                    CartItem.product
                )
                .joinedload(
                    Product.category
                ),

                # =================================================
                # VARIANT
                # =================================================
                #
                # VERY IMPORTANT
                #
                # This prevents:
                #
                # sqlalchemy.exc.MissingGreenlet
                #
                # when accessing:
                #
                # item.variant
                #
                # =================================================

                joinedload(
                    CartItem.variant
                ),
            )
            .where(
                CartItem.user_id == user_id
            )
            .order_by(
                CartItem.created_at.desc()
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(
                page_size
            )
        )

        cart_items = (
            result
            .unique()
            .scalars()
            .all()
        )

        return (
            cart_items,
            total_records,
        )

    # ============================================================
    # GET ALL CART ITEMS
    # ============================================================

    @staticmethod
    async def get_all_cart_items(
        db: AsyncSession,
        user_id: UUID,
    ):
        """
        Get all cart items for checkout/order creation.

        Product and Variant are eagerly loaded because
        OrderService accesses:

            item.product
            item.variant

        in async code.
        """

        result = await db.execute(
            select(CartItem)
            .options(

                # =================================================
                # PRODUCT
                # =================================================

                joinedload(
                    CartItem.product
                )
                .joinedload(
                    Product.category
                ),

                joinedload(
                    CartItem.product
                )
                .joinedload(
                    Product.images
                ),

                # =================================================
                # VARIANT
                # =================================================

                joinedload(
                    CartItem.variant
                ),
            )
            .where(
                CartItem.user_id == user_id
            )
            .order_by(
                CartItem.created_at.asc()
            )
        )

        return (
            result
            .unique()
            .scalars()
            .all()
        )

    # ============================================================
    # DELETE ONE CART ITEM
    # ============================================================

    @staticmethod
    async def delete(
        db: AsyncSession,
        cart_item: CartItem,
    ):
        await db.delete(cart_item)

        await db.commit()

        return True

    # ============================================================
    # CLEAR ENTIRE CART
    # ============================================================

    @staticmethod
    async def clear_cart(
        db: AsyncSession,
        user_id: UUID,
    ):
        """
        Delete all cart items belonging to the user.

        This should be called AFTER successful payment.

        IMPORTANT:
        This method commits its own transaction.

        If you want cart deletion to be part of the same
        payment transaction, use clear_cart_without_commit()
        below instead.
        """

        result = await db.execute(
            select(CartItem)
            .where(
                CartItem.user_id == user_id
            )
        )

        cart_items = (
            result
            .scalars()
            .all()
        )

        if not cart_items:
            return True

        for cart_item in cart_items:
            await db.delete(cart_item)

        await db.commit()

        return True

    # ============================================================
    # CLEAR CART WITHOUT COMMIT
    # ============================================================

    @staticmethod
    async def clear_cart_without_commit(
        db: AsyncSession,
        user_id: UUID,
    ):
        """
        Delete all cart items WITHOUT committing.

        Recommended for payment-success transactions.

        Example:

            payment = PAID
            stock -= quantity
            order = CONFIRMED

            await CartRepository.clear_cart_without_commit(
                db,
                user_id
            )

            await db.commit()

        This makes payment + stock + cart clearing part of
        the same database transaction.
        """

        result = await db.execute(
            select(CartItem)
            .where(
                CartItem.user_id == user_id
            )
        )

        cart_items = (
            result
            .scalars()
            .all()
        )

        for cart_item in cart_items:
            await db.delete(cart_item)

        return True

    # ============================================================
    # CHECK WHETHER CART IS EMPTY
    # ============================================================

    @staticmethod
    async def is_cart_empty(
        db: AsyncSession,
        user_id: UUID,
    ) -> bool:

        result = await db.execute(
            select(
                func.count(CartItem.id)
            )
            .where(
                CartItem.user_id == user_id
            )
        )

        count = result.scalar() or 0

        return count == 0

    # ============================================================
    # GET CART ITEM COUNT
    # ============================================================

    @staticmethod
    async def get_cart_count(
        db: AsyncSession,
        user_id: UUID,
    ):

        result = await db.execute(
            select(
                func.coalesce(
                    func.sum(
                        CartItem.quantity
                    ),
                    0,
                )
            )
            .where(
                CartItem.user_id == user_id
            )
        )

        return result.scalar() or 0