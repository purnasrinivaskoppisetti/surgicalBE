from datetime import datetime, timedelta

from sqlalchemy import (
    func,
    distinct,
    extract,
    desc,
)
from sqlalchemy.future import select

from app.models.models import (
    User,
    Order,
    OrderItem,
    Product,
    Category,
    CartItem,
    OrderStatus,
    PaymentStatus,
)


class DashboardRepository:

    # ============================================================
    # DASHBOARD SUMMARY
    # ============================================================

    @staticmethod
    async def get_summary(db):

        today = datetime.utcnow().date()

        # --------------------------------------------------------
        # ONLY PAID + NON-CANCELLED ORDERS
        # --------------------------------------------------------

        paid_order_filter = (
            Order.payment_status == PaymentStatus.PAID,
            Order.status != OrderStatus.CANCELLED,
        )

        # --------------------------------------------------------
        # TOTAL REVENUE
        # --------------------------------------------------------

        revenue = await db.scalar(
            select(
                func.coalesce(
                    func.sum(Order.total_amount),
                    0
                )
            )
            .where(*paid_order_filter)
        )

        # --------------------------------------------------------
        # ORDERS TODAY
        # ONLY SUCCESSFULLY PAID ORDERS
        # --------------------------------------------------------

        orders_today = await db.scalar(
            select(
                func.count(Order.id)
            )
            .where(
                func.date(Order.created_at) == today,
                *paid_order_filter
            )
        )

        # --------------------------------------------------------
        # PENDING DELIVERIES
        # ONLY PAID ORDERS
        # --------------------------------------------------------

        pending_deliveries = await db.scalar(
            select(
                func.count(Order.id)
            )
            .where(
                Order.payment_status == PaymentStatus.PAID,
                Order.status.in_([
                    OrderStatus.CONFIRMED,
                    OrderStatus.PACKED,
                    OrderStatus.SHIPPED,
                    OrderStatus.OUT_FOR_DELIVERY,
                ])
            )
        )

        # --------------------------------------------------------
        # TOTAL CUSTOMERS
        # --------------------------------------------------------

        total_customers = await db.scalar(
            select(
                func.count(User.id)
            )
            .where(
                User.role == "customer"
            )
        )

        # --------------------------------------------------------
        # UNIQUE PAID BUYERS
        # --------------------------------------------------------

        unique_buyers = await db.scalar(
            select(
                func.count(
                    distinct(Order.user_id)
                )
            )
            .where(*paid_order_filter)
        )

        # --------------------------------------------------------
        # CONVERSION RATE
        # --------------------------------------------------------

        conversion_rate = (
            (unique_buyers / total_customers) * 100
            if total_customers
            else 0
        )

        # --------------------------------------------------------
        # REPEAT PAID CUSTOMERS
        # --------------------------------------------------------

        repeat_customers = await db.scalar(
            select(
                func.count()
            )
            .select_from(
                select(
                    Order.user_id
                )
                .where(*paid_order_filter)
                .group_by(
                    Order.user_id
                )
                .having(
                    func.count(Order.id) > 1
                )
                .subquery()
            )
        )

        # --------------------------------------------------------
        # RETURNING CUSTOMER %
        # --------------------------------------------------------

        returning_percentage = (
            (repeat_customers / total_customers) * 100
            if total_customers
            else 0
        )

        return {
            "total_revenue": float(
                revenue or 0
            ),

            "orders_today": int(
                orders_today or 0
            ),

            "pending_deliveries": int(
                pending_deliveries or 0
            ),

            "total_customers": int(
                total_customers or 0
            ),

            "conversion_rate": round(
                conversion_rate,
                2
            ),

            "returning_customers_percentage": round(
                returning_percentage,
                2
            ),
        }

    # ============================================================
    # REVENUE TREND - LAST 14 DAYS
    # ONLY PAID + NON-CANCELLED ORDERS
    # ============================================================

    @staticmethod
    async def get_revenue_trend(db):

        last_14_days = (
            datetime.utcnow() - timedelta(days=14)
        )

        result = await db.execute(
            select(
                func.date(Order.created_at),
                func.coalesce(
                    func.sum(Order.total_amount),
                    0
                )
            )
            .where(
                Order.created_at >= last_14_days,
                Order.payment_status == PaymentStatus.PAID,
                Order.status != OrderStatus.CANCELLED,
            )
            .group_by(
                func.date(Order.created_at)
            )
            .order_by(
                func.date(Order.created_at)
            )
        )

        return [
            {
                "date": str(row[0]),
                "revenue": float(row[1] or 0),
            }
            for row in result.all()
        ]

    # ============================================================
    # ORDERS BY CATEGORY
    # ONLY PAID + NON-CANCELLED ORDERS
    # ============================================================

    @staticmethod
    async def get_orders_by_category(db):

        result = await db.execute(
            select(
                Category.name,
                func.coalesce(
                    func.sum(OrderItem.quantity),
                    0
                )
            )
            .join(
                Product,
                Product.category_id == Category.id
            )
            .join(
                OrderItem,
                OrderItem.product_id == Product.id
            )
            .join(
                Order,
                Order.id == OrderItem.order_id
            )
            .where(
                Order.payment_status == PaymentStatus.PAID,
                Order.status != OrderStatus.CANCELLED,
            )
            .group_by(
                Category.name
            )
            .order_by(
                desc(
                    func.sum(OrderItem.quantity)
                )
            )
        )

        rows = result.all()

        total = sum(
            (row[1] or 0)
            for row in rows
        )

        return [
            {
                "category_name": row[0],
                "total_orders": int(
                    row[1] or 0
                ),
                "percentage": (
                    round(
                        ((row[1] or 0) / total) * 100,
                        2
                    )
                    if total
                    else 0
                ),
            }
            for row in rows
        ]

    # ============================================================
    # PEAK SHOPPING HOURS
    # ONLY PAID + NON-CANCELLED ORDERS
    # ============================================================

    @staticmethod
    async def get_peak_shopping_hours(db):

        result = await db.execute(
            select(
                extract(
                    "hour",
                    Order.created_at
                ),
                func.count(Order.id)
            )
            .where(
                Order.payment_status == PaymentStatus.PAID,
                Order.status != OrderStatus.CANCELLED,
            )
            .group_by(
                extract(
                    "hour",
                    Order.created_at
                )
            )
            .order_by(
                extract(
                    "hour",
                    Order.created_at
                )
            )
        )

        return [
            {
                "hour": f"{int(row[0]):02d}:00",
                "orders_count": int(
                    row[1] or 0
                ),
            }
            for row in result.all()
        ]

    # ============================================================
    # TOP SELLING PRODUCTS
    # ONLY PAID + NON-CANCELLED ORDERS
    # ============================================================

    @staticmethod
    async def get_top_selling_products(db):

        result = await db.execute(
            select(
                Product.id,
                Product.name,
                func.coalesce(
                    func.sum(OrderItem.quantity),
                    0
                ),
                func.coalesce(
                    func.sum(OrderItem.total),
                    0
                ),
            )
            .join(
                OrderItem,
                OrderItem.product_id == Product.id
            )
            .join(
                Order,
                Order.id == OrderItem.order_id
            )
            .where(
                Order.payment_status == PaymentStatus.PAID,
                Order.status != OrderStatus.CANCELLED,
            )
            .group_by(
                Product.id,
                Product.name
            )
            .order_by(
                desc(
                    func.sum(OrderItem.quantity)
                )
            )
            .limit(5)
        )

        return [
            {
                "product_id": str(row[0]),
                "product_name": row[1],
                "total_sold": int(
                    row[2] or 0
                ),
                "revenue": float(
                    row[3] or 0
                ),
            }
            for row in result.all()
        ]

    # ============================================================
    # RECENT PAID ORDERS
    # ONLY PAID + NON-CANCELLED ORDERS
    # ============================================================

    @staticmethod
    async def get_recent_orders(db):

        result = await db.execute(
            select(
                Order.order_number,
                User.full_name,
                Order.total_amount,
                Order.status,
            )
            .join(
                User,
                User.id == Order.user_id
            )
            .where(
                Order.payment_status == PaymentStatus.PAID,
                Order.status != OrderStatus.CANCELLED,
            )
            .order_by(
                Order.created_at.desc()
            )
            .limit(10)
        )

        return [
            {
                "order_number": row[0],
                "customer_name": row[1],
                "amount": float(
                    row[2] or 0
                ),
                "status": (
                    row[3].value
                    if row[3]
                    else None
                ),
            }
            for row in result.all()
        ]

    # ============================================================
    # ABANDONED CARTS
    #
    # This is intentionally NOT filtered by payment status because
    # abandoned carts are carts where no completed order exists.
    # ============================================================

    @staticmethod
    async def get_abandoned_carts(db):

        result = await db.execute(
            select(
                User.full_name,
                func.count(CartItem.id),
                func.coalesce(
                    func.sum(
                        CartItem.quantity *
                        Product.sale_price
                    ),
                    0
                ),
            )
            .join(
                CartItem,
                CartItem.user_id == User.id
            )
            .join(
                Product,
                Product.id == CartItem.product_id
            )
            .group_by(
                User.id,
                User.full_name
            )
            .order_by(
                desc(
                    func.sum(
                        CartItem.quantity *
                        Product.sale_price
                    )
                )
            )
            .limit(5)
        )

        return [
            {
                "customer_name": row[0],
                "items_count": int(
                    row[1] or 0
                ),
                "cart_value": float(
                    row[2] or 0
                ),
            }
            for row in result.all()
        ]