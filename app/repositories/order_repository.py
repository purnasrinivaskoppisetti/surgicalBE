# app/repositories/order_repository.py

from sqlalchemy import select, func, case, or_
from sqlalchemy.orm import joinedload

from app.models.models import (
    Coupon,
    StoreSetting,
    Order,
    OrderItem,
    User,
    OrderStatus,
    PaymentStatus,
)


class OrderRepository:

    @staticmethod
    async def get_coupon_by_code(db, code: str):
        result = await db.execute(
            select(Coupon).where(
                Coupon.code == code,
                Coupon.is_active == True
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_store_settings(db):
        result = await db.execute(
            select(StoreSetting)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_order(db, order: Order):
        db.add(order)
        await db.flush()
        return order

    @staticmethod
    async def create_order_item(db, order_item: OrderItem):
        db.add(order_item)
        await db.flush()
        return order_item

    # ============================================================
    # GET SINGLE ORDER - ADMIN
    # ============================================================

    @staticmethod
    async def get_order_by_id(db, order_id):

        result = await db.execute(
            select(Order)
            .options(
                joinedload(Order.user),

                joinedload(
                    Order.items
                ).joinedload(
                    OrderItem.product
                ),

                joinedload(Order.address),

                joinedload(Order.payments),

                joinedload(Order.shipments),
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



    
    # ============================================================
    # GET CUSTOMER ORDER
    # ============================================================

    @staticmethod
    async def get_customer_order(
        db,
        order_id,
        user_id,
    ):

        result = await db.execute(
            select(Order)
            .options(
                joinedload(Order.user),

                joinedload(
                    Order.items
                ).joinedload(
                    OrderItem.product
                ),

                joinedload(Order.address),

                joinedload(Order.payments),

                joinedload(Order.shipments),
            )
            .where(
                Order.id == order_id,
                Order.user_id == user_id,
            )
        )

        return (
            result
            .unique()
            .scalar_one_or_none()
        )



    # ============================================================
        # GET ALL ORDERS FOR CUSTOMER
        # ============================================================
    
    @staticmethod
    async def get_orders_by_user(db, user_id):
            result = await db.execute(
                select(Order)
                .options(
                    joinedload(Order.items).joinedload(OrderItem.product),
                    joinedload(Order.address),
                    joinedload(Order.payments),
                    joinedload(Order.shipments),
                    joinedload(Order.coupon),
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

    # ============================================================
    # GET ORDERS FOR ADMIN
    #
    # IMPORTANT:
    # DEFAULT = ONLY PAID ORDERS
    # ============================================================

    @staticmethod
    async def get_orders(
        db,
        page: int,
        page_size: int,
        search=None,
        status=None,
        payment_status=None,
    ):

        conditions = []

        # --------------------------------------------------------
        # ONLY PAID ORDERS BY DEFAULT
        # --------------------------------------------------------

        if payment_status:
            conditions.append(
                Order.payment_status == payment_status
            )
        else:
            conditions.append(
                Order.payment_status == PaymentStatus.PAID
            )

        # --------------------------------------------------------
        # ORDER STATUS FILTER
        # --------------------------------------------------------

        if status:
            conditions.append(
                Order.status == status
            )

        # --------------------------------------------------------
        # SEARCH
        # --------------------------------------------------------

        if search:

            conditions.append(
                or_(
                    Order.order_number.ilike(
                        f"%{search}%"
                    ),

                    User.full_name.ilike(
                        f"%{search}%"
                    ),

                    User.phone.ilike(
                        f"%{search}%"
                    ),
                )
            )

        # ========================================================
        # COUNT
        # ========================================================

        count_query = (
            select(
                func.count(Order.id)
            )
            .join(User)
            .where(*conditions)
        )

        total = await db.scalar(
            count_query
        )

        # ========================================================
        # MAIN QUERY
        # ========================================================

        query = (
            select(Order)
            .join(User)
            .options(

                joinedload(
                    Order.user
                ),

                joinedload(
                    Order.address
                ),

                joinedload(
                    Order.items
                ).joinedload(
                    OrderItem.product
                ),

                joinedload(
                    Order.payments
                ),

                joinedload(
                    Order.shipments
                ),
            )
            .where(*conditions)
            .order_by(
                Order.created_at.desc()
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(page_size)
        )

        result = await db.execute(
            query
        )

        orders = (
            result
            .unique()
            .scalars()
            .all()
        )

        return (
            orders,
            total or 0
        )

    # ============================================================
    # UPDATE ORDER STATUS
    # ============================================================

    @staticmethod
    async def update_order_status(
        db,
        order_id,
        status,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id
            )
        )

        if not order:
            return None

        order.status = status

        await db.commit()

        await db.refresh(
            order
        )

        return order

    # ============================================================
    # UPDATE PAYMENT STATUS
    # ============================================================

    @staticmethod
    async def update_payment_status(
        db,
        order_id,
        payment_status,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id
            )
        )

        if not order:
            return None

        order.payment_status = (
            payment_status
        )

        await db.commit()

        await db.refresh(
            order
        )

        return order

    # ============================================================
    # CANCEL ORDER
    # ============================================================

    @staticmethod
    async def cancel_order(
        db,
        order_id,
        reason,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id
            )
        )

        if not order:
            return None

        order.status = (
            OrderStatus.CANCELLED
        )

        order.cancel_reason = reason

        await db.commit()

        await db.refresh(
            order
        )

        return order

    # ============================================================
    # SUMMARY - PAID ORDERS
    # ============================================================

    @staticmethod
    async def get_order_summary(
        db
    ):

        result = await db.execute(
            select(

                func.count(
                    Order.id
                ).label(
                    "total_orders"
                ),

                func.coalesce(
                    func.sum(
                        Order.total_amount
                    ),
                    0
                ).label(
                    "revenue"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                Order.status ==
                                OrderStatus.PENDING,
                                1
                            ),
                            else_=0
                        )
                    ),
                    0
                ).label(
                    "pending"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                Order.status.in_([
                                    OrderStatus.SHIPPED,
                                    OrderStatus.OUT_FOR_DELIVERY
                                ]),
                                1
                            ),
                            else_=0
                        )
                    ),
                    0
                ).label(
                    "in_transit"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                Order.status ==
                                OrderStatus.DELIVERED,
                                1
                            ),
                            else_=0
                        )
                    ),
                    0
                ).label(
                    "delivered"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                Order.status ==
                                OrderStatus.CANCELLED,
                                1
                            ),
                            else_=0
                        )
                    ),
                    0
                ).label(
                    "cancelled"
                ),
            )
            .where(
                Order.payment_status ==
                PaymentStatus.PAID
            )
        )

        return (
            result
            .mappings()
            .one()
        )


    @staticmethod
    async def get_orders_for_tracking(db):

        result = await db.execute(

            select(Order)

            .options(

                joinedload(
                    Order.shipments
                ),

                joinedload(
                    Order.user
                ),
            )

            .where(

                # ----------------------------------------------
                # ONLY PAID ORDERS
                # ----------------------------------------------

                Order.payment_status ==
                PaymentStatus.PAID,

                # ----------------------------------------------
                # NOT DELIVERED
                # ----------------------------------------------

                Order.status !=
                OrderStatus.DELIVERED,

                # ----------------------------------------------
                # NOT CANCELLED
                # ----------------------------------------------

                Order.status !=
                OrderStatus.CANCELLED,
            )
        )

        return (
            result
            .unique()
            .scalars()
            .all()
        )