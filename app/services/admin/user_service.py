from app.repositories.user_repository import (
    UserRepository
)

from app.models.models import (
    PaymentStatus
)


class UserService:

    @staticmethod
    async def get_customers(
        db,
        page,
        page_size,
        search=None
    ):

        customers, total = (
            await UserRepository.get_customers(
                db,
                page,
                page_size,
                search
            )
        )

        customer_data = []

        total_spent_all = 0
        total_orders_all = 0
        vip_count = 0
        repeat_customers = 0

        for customer in customers:

            customer = (
                await UserRepository
                .get_customer_details(
                    db,
                    customer.id
                )
            )

            # ========================================================
            # ONLY PAID ORDERS
            # ========================================================

            paid_orders = [
                order
                for order in customer.orders
                if order.payment_status == PaymentStatus.PAID
            ]

            # ========================================================
            # ORDER COUNT
            #
            # If you want "orders" to mean only successful/paid orders,
            # use paid_orders.
            # ========================================================

            orders_count = len(paid_orders)

            # ========================================================
            # TOTAL SPENT
            #
            # ONLY PAID ORDERS ARE INCLUDED
            # ========================================================

            total_spent = sum(
                float(order.total_amount or 0)
                for order in paid_orders
            )

            # ========================================================
            # REPEAT CUSTOMER
            # ========================================================

            if orders_count > 1:
                repeat_customers += 1

            # ========================================================
            # CUSTOMER STATUS
            # ========================================================

            if total_spent >= 30000:

                vip_count += 1
                status = "vip"

            elif orders_count >= 5:

                status = "frequent"

            else:

                status = "active"

            # ========================================================
            # SUMMARY TOTALS
            # ========================================================

            total_spent_all += total_spent
            total_orders_all += orders_count

            # ========================================================
            # CITY
            # ========================================================

            city = None

            if customer.addresses:
                city = customer.addresses[0].city

            # ========================================================
            # LAST PAID ORDER
            # ========================================================

            last_order = None

            if paid_orders:

                last_order = max(
                    paid_orders,
                    key=lambda x: x.created_at
                )

            # ========================================================
            # CUSTOMER DATA
            # ========================================================

            customer_data.append({

                "id": str(
                    customer.id
                ),

                "name": customer.full_name,

                "email": customer.email,

                "phone": customer.phone,

                "city": city,

                "orders": orders_count,

                "spent": total_spent,

                "status": status,

                "last_order": (
                    last_order.created_at
                    if last_order
                    else None
                )
            })

        # ============================================================
        # AVERAGE ORDER VALUE
        # ============================================================

        avg_order_value = 0

        if total_orders_all:

            avg_order_value = (
                total_spent_all /
                total_orders_all
            )

        # ============================================================
        # REPEAT RATE
        # ============================================================

        repeat_rate = 0

        if total:

            repeat_rate = (
                repeat_customers /
                total
            ) * 100

        # ============================================================
        # RESPONSE
        # ============================================================

        return {

            "summary": {

                "total_customers":
                    total,

                "vip_customers":
                    vip_count,

                "avg_order_value":
                    round(
                        avg_order_value,
                        2
                    ),

                "repeat_rate":
                    round(
                        repeat_rate,
                        2
                    )
            },

            "customers":
                customer_data,

            "pagination": {

                "page":
                    page,

                "page_size":
                    page_size,

                "total":
                    total
            }
        }


    # ================================================================
    # SINGLE CUSTOMER
    # ================================================================

    @staticmethod
    async def get_customer(
        db,
        customer_id
    ):

        customer = (
            await UserRepository
            .get_customer_details(
                db,
                customer_id
            )
        )

        if not customer:
            return None

        # ============================================================
        # ONLY PAID ORDERS
        # ============================================================

        paid_orders = [
            order
            for order in customer.orders
            if order.payment_status == PaymentStatus.PAID
        ]

        # ============================================================
        # ORDER COUNT
        # ============================================================

        orders_count = len(
            paid_orders
        )

        # ============================================================
        # TOTAL SPENT
        # ============================================================

        total_spent = sum(
            float(order.total_amount or 0)
            for order in paid_orders
        )

        # ============================================================
        # AVERAGE ORDER VALUE
        # ============================================================

        avg_order_value = (

            total_spent /
            orders_count

            if orders_count
            else 0
        )

        # ============================================================
        # ADDRESS
        # ============================================================

        address = None

        if customer.addresses:

            address = customer.addresses[0]

        # ============================================================
        # LATEST PAID ORDERS
        # ============================================================

        latest_orders = sorted(
            paid_orders,
            key=lambda x: x.created_at,
            reverse=True
        )[:10]

        # ============================================================
        # RESPONSE
        # ============================================================

        return {

            "id":
                str(customer.id),

            "name":
                customer.full_name,

            "email":
                customer.email,

            "phone":
                customer.phone,

            "joined_at":
                customer.created_at,

            # ========================================================
            # ADDRESS
            # ========================================================

            "address": {

                "full_name":
                    address.full_name
                    if address
                    else None,

                "address":
                    address.address_line1
                    if address
                    else None,

                "city":
                    address.city
                    if address
                    else None,

                "state":
                    address.state
                    if address
                    else None,

                "pincode":
                    address.pincode
                    if address
                    else None
            },

            # ========================================================
            # STATISTICS
            # ========================================================

            "statistics": {

                "orders":
                    orders_count,

                "spent":
                    total_spent,

                "aov":
                    round(
                        avg_order_value,
                        2
                    ),

                "wishlist":
                    len(
                        customer.wishlist_items
                    )
            },

            # ========================================================
            # ORDER HISTORY
            #
            # ONLY PAID ORDERS
            # ========================================================

            "orders_history": [

                {

                    "order_id":
                        str(order.id),

                    "order_number":
                        order.order_number,

                    "amount":
                        float(
                            order.total_amount
                        ),

                    "status":
                        order.status.value,

                    "payment_status":
                        order.payment_status.value,

                    "date":
                        order.created_at
                }

                for order in latest_orders
            ],

            # ========================================================
            # ACTIVITY TIMELINE
            # ========================================================

            "activity_timeline": [

                {

                    "title":
                        "Joined Surgical World",

                    "date":
                        customer.created_at
                }

            ]
        }