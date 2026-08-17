from sqlalchemy import (
    select,
    func,
    case,
    or_,
)

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload

from app.models.models import (
    Coupon,
    StoreSetting,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    User,
    OrderStatus,
    PaymentStatus,
    OrderStatusHistory,
)


class OrderRepository:

    # ============================================================
    # GET COUPON BY CODE
    # ============================================================

    @staticmethod
    async def get_coupon_by_code(
        db: AsyncSession,
        code: str,
    ):
        result = await db.execute(
            select(Coupon).where(
                Coupon.code == code,
                Coupon.is_active == True,
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # GET STORE SETTINGS
    # ============================================================

    @staticmethod
    async def get_store_settings(
        db: AsyncSession,
    ):
        result = await db.execute(
            select(StoreSetting)
        )

        return result.scalar_one_or_none()

    # ============================================================
    # CREATE ORDER
    # ============================================================

    @staticmethod
    async def create_order(
        db: AsyncSession,
        order: Order,
    ):
        db.add(order)

        await db.flush()

        return order

    # ============================================================
    # CREATE ORDER ITEM
    # ============================================================

    @staticmethod
    async def create_order_item(
        db: AsyncSession,
        order_item: OrderItem,
    ):
        db.add(order_item)

        await db.flush()

        return order_item

    # ============================================================
    # GET ORDER BY ID
    #
    # Loads:
    # - User
    # - Order items
    # - Product
    # - Product category
    # - Product images
    # - Product variant
    # - Address
    # - Payments
    # - Shipments
    # - Coupon
    # ============================================================

    @staticmethod
    async def get_order_by_id(
        db: AsyncSession,
        order_id,
    ):

        result = await db.execute(

            select(Order)

            .options(

                # ------------------------------------------------
                # USER
                # ------------------------------------------------

                joinedload(
                    Order.user
                ),

                # ------------------------------------------------
                # ORDER ITEMS → PRODUCT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.category
                ),

                # ------------------------------------------------
                # ORDER ITEMS → PRODUCT IMAGES
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.images
                ),

                # ------------------------------------------------
                # ORDER ITEMS → VARIANT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.variant
                ),

                # ------------------------------------------------
                # ADDRESS
                # ------------------------------------------------

                joinedload(
                    Order.address
                ),

                # ------------------------------------------------
                # PAYMENTS
                # ------------------------------------------------

                joinedload(
                    Order.payments
                ),

                # ------------------------------------------------
                # SHIPMENTS
                # ------------------------------------------------

                joinedload(
                    Order.shipments
                ),

                # ------------------------------------------------
                # COUPON
                # ------------------------------------------------

                joinedload(
                    Order.coupon
                ),
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
    #
    # IMPORTANT:
    # Checks both:
    #
    # order_id
    # user_id
    #
    # So a customer cannot access another customer's order.
    # ============================================================

    @staticmethod
    async def get_customer_order(
        db: AsyncSession,
        order_id,
        user_id,
    ):

        result = await db.execute(

            select(Order)

            .options(

                # ------------------------------------------------
                # USER
                # ------------------------------------------------

                joinedload(
                    Order.user
                ),

                # ------------------------------------------------
                # ITEMS → PRODUCT → CATEGORY
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.category
                ),

                # ------------------------------------------------
                # ITEMS → PRODUCT IMAGES
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.images
                ),

                # ------------------------------------------------
                # ITEMS → VARIANT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.variant
                ),

                # ------------------------------------------------
                # ADDRESS
                # ------------------------------------------------

                joinedload(
                    Order.address
                ),

                # ------------------------------------------------
                # PAYMENTS
                # ------------------------------------------------

                joinedload(
                    Order.payments
                ),

                # ------------------------------------------------
                # SHIPMENTS
                # ------------------------------------------------

                joinedload(
                    Order.shipments
                ),

                # ------------------------------------------------
                # COUPON
                # ------------------------------------------------

                joinedload(
                    Order.coupon
                ),
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
    # GET ALL CUSTOMER ORDERS
    # ============================================================

    @staticmethod
    async def get_orders_by_user(
        db: AsyncSession,
        user_id,
    ):

        result = await db.execute(

            select(Order)

            .options(

                # ------------------------------------------------
                # USER
                # ------------------------------------------------

                joinedload(
                    Order.user
                ),

                # ------------------------------------------------
                # ITEMS → PRODUCT → CATEGORY
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.category
                ),

                # ------------------------------------------------
                # ITEMS → PRODUCT IMAGES
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.images
                ),

                # ------------------------------------------------
                # ITEMS → VARIANT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.variant
                ),

                # ------------------------------------------------
                # ADDRESS
                # ------------------------------------------------

                joinedload(
                    Order.address
                ),

                # ------------------------------------------------
                # PAYMENTS
                # ------------------------------------------------

                joinedload(
                    Order.payments
                ),

                # ------------------------------------------------
                # SHIPMENTS
                # ------------------------------------------------

                joinedload(
                    Order.shipments
                ),

                # ------------------------------------------------
                # COUPON
                # ------------------------------------------------

                joinedload(
                    Order.coupon
                ),
            )

            .where(
                Order.user_id == user_id,
                Order.payment_status == PaymentStatus.PAID
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
    # Default:
    # Only PAID orders
    #
    # Supports:
    # - pagination
    # - search
    # - order status
    # - payment status
    # ============================================================

    @staticmethod
    async def get_orders(
        db: AsyncSession,
        page: int,
        page_size: int,
        search=None,
        status=None,
        payment_status=None,
    ):

        conditions = []

        # ========================================================
        # PAYMENT STATUS
        # ========================================================

        if payment_status:

            conditions.append(
                Order.payment_status
                == payment_status
            )

        else:

            conditions.append(
                Order.payment_status
                == PaymentStatus.PAID
            )

        # ========================================================
        # ORDER STATUS
        # ========================================================

        if status:

            conditions.append(
                Order.status
                == status
            )

        # ========================================================
        # SEARCH
        # ========================================================

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
                func.count(
                    Order.id
                )
            )

            .join(
                User
            )

            .where(
                *conditions
            )
        )

        total = await db.scalar(
            count_query
        )

        # ========================================================
        # MAIN QUERY
        # ========================================================

        query = (

            select(Order)

            .join(
                User
            )

            .options(

                # ------------------------------------------------
                # USER
                # ------------------------------------------------

                joinedload(
                    Order.user
                ),

                # ------------------------------------------------
                # ADDRESS
                # ------------------------------------------------

                joinedload(
                    Order.address
                ),

                # ------------------------------------------------
                # ITEMS → PRODUCT → CATEGORY
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.category
                ),

                # ------------------------------------------------
                # ITEMS → PRODUCT IMAGES
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                )
                .joinedload(
                    Product.images
                ),

                # ------------------------------------------------
                # ITEMS → VARIANT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.variant
                ),

                # ------------------------------------------------
                # PAYMENTS
                # ------------------------------------------------

                joinedload(
                    Order.payments
                ),

                # ------------------------------------------------
                # SHIPMENTS
                # ------------------------------------------------

                joinedload(
                    Order.shipments
                ),

                # ------------------------------------------------
                # COUPON
                # ------------------------------------------------

                joinedload(
                    Order.coupon
                ),
            )

            .where(
                *conditions
            )

            .order_by(
                Order.created_at.desc()
            )

            .offset(
                (page - 1) * page_size
            )

            .limit(
                page_size
            )
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
            total or 0,
        )

    # ============================================================
    # GET ORDER STATUS HISTORY
    #
    # We query directly instead of using
    # Order.status_history relationship.
    # ============================================================

    @staticmethod
    async def get_order_status_history(
        db: AsyncSession,
        order_id,
    ):

        result = await db.execute(

            select(
                OrderStatusHistory
            )

            .where(
                OrderStatusHistory.order_id
                == order_id
            )

            .order_by(
                OrderStatusHistory.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    # ============================================================
    # UPDATE ORDER STATUS
    # ============================================================

    @staticmethod
    async def update_order_status(
        db: AsyncSession,
        order_id,
        status,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id,
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
        db: AsyncSession,
        order_id,
        payment_status,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id,
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
    #
    # NOTE:
    # Actual variant stock restoration is handled in
    # OrderService because it needs transaction/locking logic.
    # ============================================================

    @staticmethod
    async def cancel_order(
        db: AsyncSession,
        order_id,
        reason,
    ):

        order = (
            await OrderRepository
            .get_order_by_id(
                db,
                order_id,
            )
        )

        if not order:

            return None

        order.status = (
            OrderStatus.CANCELLED
        )

        order.cancel_reason = (
            reason
        )

        await db.commit()

        await db.refresh(
            order
        )

        return order

    # ============================================================
    # ORDER SUMMARY
    # ============================================================

    @staticmethod
    async def get_order_summary(
        db: AsyncSession,
    ):

        result = await db.execute(

            select(

                # ------------------------------------------------
                # TOTAL ORDERS
                # ------------------------------------------------

                func.count(
                    Order.id
                ).label(
                    "total_orders"
                ),

                # ------------------------------------------------
                # REVENUE
                # ------------------------------------------------

                func.coalesce(
                    func.sum(
                        Order.total_amount
                    ),
                    0,
                ).label(
                    "revenue"
                ),

                # ------------------------------------------------
                # PENDING
                # ------------------------------------------------

                func.coalesce(

                    func.sum(

                        case(

                            (
                                Order.status
                                ==
                                OrderStatus.PENDING,

                                1,
                            ),

                            else_=0,

                        )

                    ),

                    0,

                ).label(
                    "pending"
                ),

                # ------------------------------------------------
                # IN TRANSIT
                # ------------------------------------------------

                func.coalesce(

                    func.sum(

                        case(

                            (

                                Order.status.in_([
                                    OrderStatus.SHIPPED,
                                    OrderStatus.OUT_FOR_DELIVERY,
                                ]),

                                1,

                            ),

                            else_=0,

                        )

                    ),

                    0,

                ).label(
                    "in_transit"
                ),

                # ------------------------------------------------
                # DELIVERED
                # ------------------------------------------------

                func.coalesce(

                    func.sum(

                        case(

                            (

                                Order.status
                                ==
                                OrderStatus.DELIVERED,

                                1,

                            ),

                            else_=0,

                        )

                    ),

                    0,

                ).label(
                    "delivered"
                ),

                # ------------------------------------------------
                # CANCELLED
                # ------------------------------------------------

                func.coalesce(

                    func.sum(

                        case(

                            (

                                Order.status
                                ==
                                OrderStatus.CANCELLED,

                                1,

                            ),

                            else_=0,

                        )

                    ),

                    0,

                ).label(
                    "cancelled"
                ),

            )

            .where(
                Order.payment_status
                ==
                PaymentStatus.PAID
            )
        )

        return (
            result
            .mappings()
            .one()
        )

    # ============================================================
    # GET ORDERS FOR TRACKING
    #
    # Used by Blue Dart synchronization.
    #
    # Gets:
    # - Paid orders
    # - Not delivered
    # - Not cancelled
    # - Shipments
    # - User
    # - Items
    # - Variants
    # ============================================================

    @staticmethod
    async def get_orders_for_tracking(
        db: AsyncSession,
    ):

        result = await db.execute(

            select(Order)

            .options(

                # ------------------------------------------------
                # SHIPMENTS
                # ------------------------------------------------

                joinedload(
                    Order.shipments
                ),

                # ------------------------------------------------
                # USER
                # ------------------------------------------------

                joinedload(
                    Order.user
                ),

                # ------------------------------------------------
                # ADDRESS
                # ------------------------------------------------

                joinedload(
                    Order.address
                ),

                # ------------------------------------------------
                # ITEMS → PRODUCT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.product
                ),

                # ------------------------------------------------
                # ITEMS → VARIANT
                # ------------------------------------------------

                joinedload(
                    Order.items
                )
                .joinedload(
                    OrderItem.variant
                ),
            )

            .where(

                Order.payment_status
                ==
                PaymentStatus.PAID,

                Order.status
                !=
                OrderStatus.DELIVERED,

                Order.status
                !=
                OrderStatus.CANCELLED,

            )
        )

        return (
            result
            .unique()
            .scalars()
            .all()
        )