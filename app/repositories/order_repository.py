from sqlalchemy import select

from sqlalchemy.orm import (
    joinedload
)

from app.models.models import (
    Coupon,
    StoreSetting,
    Order,
    OrderItem,
    Product
)


class OrderRepository:

    @staticmethod
    async def get_coupon_by_code(
        db,
        code: str
    ):

        result = await db.execute(
            select(Coupon)
            .where(
                Coupon.code == code,
                Coupon.is_active == True
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_store_settings(
        db
    ):

        result = await db.execute(
            select(StoreSetting)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create_order(
        db,
        order: Order
    ):

        db.add(order)

        await db.flush()

        return order

    @staticmethod
    async def create_order_item(
        db,
        order_item: OrderItem
    ):

        db.add(order_item)

        await db.flush()

        return order_item

    @staticmethod
    async def get_order_by_id(
        db,
        order_id
    ):

        result = await db.execute(
            select(Order)
            .options(
                joinedload(Order.items)
                .joinedload(OrderItem.product),

                joinedload(Order.payments),

                joinedload(Order.address)
            )
            .where(
                Order.id == order_id
            )
        )

        return (
            result
            .unique()
            .scalar_one_or_none()
        )

    @staticmethod
    async def get_orders_by_user(
        db,
        user_id
    ):

        result = await db.execute(
            select(Order)
            .options(
                joinedload(Order.items)
                .joinedload(OrderItem.product),

                joinedload(Order.payments),

                joinedload(Order.address)
            )
            .where(
                Order.user_id == user_id
            )
            .order_by(
                Order.created_at.desc()
            )
        )

        return (
            result
            .unique()
            .scalars()
            .all()
        )

    @staticmethod
    async def get_order_details(
        db,
        order_id,
        user_id
    ):

        result = await db.execute(
            select(Order)
            .options(
                joinedload(Order.items)
                .joinedload(OrderItem.product),

                joinedload(Order.payments),

                joinedload(Order.address)
            )
            .where(
                Order.id == order_id,
                Order.user_id == user_id
            )
        )

        return (
            result
            .unique()
            .scalar_one_or_none()
        )

    @staticmethod
    async def update_order(
        db,
        order
    ):

        await db.commit()

        await db.refresh(order)

        return order

    @staticmethod
    async def commit(
        db
    ):

        await db.commit()