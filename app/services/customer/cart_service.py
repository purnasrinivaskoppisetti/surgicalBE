from uuid import UUID

from app.models.models import CartItem

from app.repositories.cart_repository import (
    CartRepository
)

from app.repositories.product_repository import (
    ProductRepository
)

from app.utils.pagination import build_pagination


class CartService:

    @staticmethod
    async def add_to_cart(
        db,
        user_id: UUID,
        product_id: UUID,
        quantity: int
    ):

        product = await ProductRepository.get_by_id(
            db,
            product_id
        )

        if not product:
            return {
                "success": False,
                "status_code": 404,
                "message": "Product not found"
            }

        if product.stock_qty <= 0:
            return {
                "success": False,
                "status_code": 400,
                "message": "Product is out of stock"
            }

        existing = await CartRepository.get_by_user_and_product(
            db,
            user_id,
            product_id
        )

        if existing:

            existing.quantity += quantity

            await CartRepository.update(
                db,
                existing
            )

            return {
                "success": True,
                "status_code": 200,
                "message": "Cart updated successfully"
            }

        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )

        await CartRepository.create(
            db,
            cart_item
        )

        return {
            "success": True,
            "status_code": 201,
            "message": "Product added to cart"
        }

    @staticmethod
    async def get_cart(
        db,
        user_id: UUID,
        page: int,
        page_size: int
    ):

        items, total_records = (
            await CartRepository.get_cart_items(
                db=db,
                user_id=user_id,
                page=page,
                page_size=page_size
            )
        )

        if not items:

            return {
                "success": True,
                "status_code": 200,
                "message": "Cart is empty",
                "data": [],
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_records": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False
                }
            }

        response_data = []

        subtotal = 0

        for item in items:

            product = item.product

            item_total = (
                float(product.sale_price)
                * item.quantity
            )

            subtotal += item_total

            response_data.append(
                {
                    "cart_id": str(item.id),

                    "product_id": str(product.id),

                    "category_id": str(product.category_id)
                    if product.category_id
                    else None,

                    "category_name": (
                        product.category.name
                        if product.category
                        else None
                    ),

                    "name": product.name,
                    "slug": product.slug,
                    "sku": product.sku,
                    "brand": product.brand,

                    "mrp": float(product.mrp),
                    "sale_price": float(product.sale_price),

                    "quantity": item.quantity,

                    "item_total": item_total,

                    "stock_qty": product.stock_qty,

                    "thumbnail_url": product.thumbnail_url,

                    "images": [
                        {
                            "id": str(img.id),
                            "image_url": img.image_url,
                            "is_primary": img.is_primary,
                            "sort_order": img.sort_order
                        }
                        for img in product.images
                    ]
                }
            )

        return {
            "success": True,
            "status_code": 200,
            "message": "Cart fetched successfully",
            "data": response_data,
            "cart_summary": {
                "subtotal": subtotal,
                "total_items": len(items)
            },
            "pagination": build_pagination(
                page=page,
                page_size=page_size,
                total_records=total_records
            )
        }

    @staticmethod
    async def remove_from_cart(
        db,
        user_id: UUID,
        product_id: UUID
    ):

        item = await CartRepository.get_by_user_and_product(
            db,
            user_id,
            product_id
        )

        if not item:

            return {
                "success": False,
                "status_code": 404,
                "message": "Product not found in cart"
            }

        await CartRepository.delete(
            db,
            item
        )

        return {
            "success": True,
            "status_code": 200,
            "message": "Product removed from cart"
        }