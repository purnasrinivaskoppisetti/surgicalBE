from app.repositories.order_repository import (
    OrderRepository
)


class OrderService:

    @staticmethod
    async def get_orders(
        db,
        page: int,
        page_size: int,
        search=None,
        status=None,
        payment_status=None
    ):

        orders, total = await OrderRepository.get_orders(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            payment_status=payment_status
        )

        return {
            "orders": [
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "customer_name": (
                        order.user.full_name
                        if order.user else None
                    ),
                    "customer_phone": (
                        order.user.phone
                        if order.user else None
                    ),
                    "items_count": len(order.items),
                    "amount": float(order.total_amount),
                    "payment_status": (
                        order.payment_status.value
                        if order.payment_status
                        else None
                    ),
                    "status": (
                        order.status.value
                        if order.status
                        else None
                    ),
                    "order_date": order.created_at
                }
                for order in orders
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total
            }
        }

    @staticmethod
    async def get_order(
        db,
        order_id
    ):

        order = await OrderRepository.get_order_by_id(
            db,
            order_id
        )

        if not order:
            return None

        return {
            "id": str(order.id),

            "order_number": order.order_number,

            "customer": {
                "name": (
                    order.user.full_name
                    if order.user else None
                ),
                "phone": (
                    order.user.phone
                    if order.user else None
                ),
                "email": (
                    order.user.email
                    if order.user else None
                )
            },

            "shipping_address": {
                "full_name": (
                    order.address.full_name
                    if order.address else None
                ),
                "phone": (
                    order.address.phone
                    if order.address else None
                ),
                "address": (
                    order.address.address_line1
                    if order.address else None
                ),
                "city": (
                    order.address.city
                    if order.address else None
                ),
                "state": (
                    order.address.state
                    if order.address else None
                ),
                "pincode": (
                    order.address.pincode
                    if order.address else None
                )
            },

            "items": [
                {
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": float(item.price),
                    "total": float(item.total)
                }
                for item in order.items
            ],

            "pricing": {
                "subtotal": float(order.subtotal),
                "gst": float(order.gst_amount),
                "shipping": float(order.shipping_charge),
                "discount": float(order.discount),
                "grand_total": float(order.total_amount)
            },

            "status": (
                order.status.value
                if order.status else None
            ),

            "payment_status": (
                order.payment_status.value
                if order.payment_status else None
            )
        }

    @staticmethod
    async def update_status(
        db,
        order_id,
        status
    ):

        return await OrderRepository.update_order_status(
            db,
            order_id,
            status
        )

    @staticmethod
    async def update_payment_status(
        db,
        order_id,
        payment_status
    ):

        return await OrderRepository.update_payment_status(
            db,
            order_id,
            payment_status
        )

    @staticmethod
    async def cancel_order(
        db,
        order_id,
        reason
    ):

        return await OrderRepository.cancel_order(
            db,
            order_id,
            reason
        )